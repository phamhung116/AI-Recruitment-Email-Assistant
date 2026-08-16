from collections.abc import Iterator

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base
from app.db.seed import seed_candidates
from app.models import (
    AuditLog,
    Candidate,
    DraftRevision,
    LogicalSendOperation,
    ProviderAttempt,
)


TARGET_TABLES = {
    "candidates": Candidate,
    "draft_revisions": DraftRevision,
    "logical_send_operations": LogicalSendOperation,
    "provider_attempts": ProviderAttempt,
    "audit_logs": AuditLog,
}


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def make_candidate(application_id: str = "APP-TEST-001") -> Candidate:
    return Candidate(
        application_id=application_id,
        full_name="Candidate Test",
        email="candidate@example.com",
        stage="CV_SCREENING",
        status="PASS_CV",
    )


def make_draft(candidate: Candidate, revision_number: int = 1) -> DraftRevision:
    return DraftRevision(
        candidate=candidate,
        revision_number=revision_number,
        template_code="INTERVIEW_INVITATION",
        stage="CV_SCREENING",
        decision="PASS_CV",
        to_email=candidate.email,
        subject="Interview invitation",
        decision_critical_content="You passed CV screening.",
        editable_content="Hello Candidate Test,",
        rendered_body="Hello Candidate Test,\n\nYou passed CV screening.",
        status="READY_TO_SEND",
    )


def constraint_names(model: type) -> set[str]:
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if constraint.name is not None
    }


def test_five_target_models_have_exact_approved_columns() -> None:
    expected_columns = {
        "candidates": {
            "id", "application_id", "full_name", "email", "phone", "position",
            "stage", "status", "communicated_decision", "communicated_stage",
            "communicated_at", "status_updated_at", "status_updated_by",
            "interview_time", "interviewer", "note", "created_at", "updated_at",
        },
        "draft_revisions": {
            "id", "candidate_id", "revision_number", "template_code", "stage",
            "decision", "to_email", "subject", "decision_critical_content",
            "editable_content", "rendered_body", "status", "is_correction",
            "correction_rationale", "prior_operation_id", "risk_check_result",
            "created_by", "superseded_at", "discarded_at", "created_at", "updated_at",
        },
        "logical_send_operations": {
            "id", "draft_revision_id", "operation_status", "provider_name",
            "provider_message_id", "final_outcome", "failure_category",
            "resolution_mode", "resolution_rationale", "resolved_by", "resolved_at",
            "created_by", "created_at", "updated_at",
        },
        "provider_attempts": {
            "id", "operation_id", "attempt_number", "request_payload_digest",
            "attempt_status", "http_status_code", "provider_message_id", "error_code",
            "error_message", "latency_ms", "initiated_at", "completed_at",
        },
        "audit_logs": {
            "id", "event_name", "entity_type", "entity_id", "application_id", "actor",
            "action_outcome", "payload_json", "created_at",
        },
    }

    assert {
        table_name: set(model.__table__.columns.keys())
        for table_name, model in TARGET_TABLES.items()
    } == expected_columns


def test_approved_unique_and_check_constraints_are_named() -> None:
    assert {
        "candidates_uq_application_id",
        "candidates_ck_name",
        "candidates_ck_email",
        "candidates_ck_stage",
        "candidates_ck_status",
    }.issubset(constraint_names(Candidate))
    assert {
        "uq_draft_revisions_candidate_rev",
        "draft_revisions_ck_positive_number",
        "draft_revisions_ck_template_code",
        "draft_revisions_ck_status",
        "draft_revisions_ck_correction_rationale",
    }.issubset(constraint_names(DraftRevision))
    assert "logical_send_operations_uq_draft_rev" in constraint_names(LogicalSendOperation)
    assert "uq_provider_attempts_op_attempt" in constraint_names(ProviderAttempt)
    assert "audit_logs_ck_event_name" in constraint_names(AuditLog)

    assert any(isinstance(item, UniqueConstraint) for item in Candidate.__table__.constraints)
    assert any(isinstance(item, CheckConstraint) for item in AuditLog.__table__.constraints)


def test_foreign_keys_use_restrict_actions() -> None:
    expected = {
        ("draft_revisions", "candidate_id"): "candidates.id",
        ("draft_revisions", "prior_operation_id"): "logical_send_operations.id",
        ("logical_send_operations", "draft_revision_id"): "draft_revisions.id",
        ("provider_attempts", "operation_id"): "logical_send_operations.id",
    }

    for (table_name, column_name), target in expected.items():
        foreign_key = next(iter(Base.metadata.tables[table_name].c[column_name].foreign_keys))
        assert foreign_key.target_fullname == target
        assert foreign_key.ondelete == "RESTRICT"
        assert foreign_key.onupdate == "RESTRICT"


def test_approved_workload_indexes_are_present() -> None:
    index_names = {
        index.name
        for model in TARGET_TABLES.values()
        for index in model.__table__.indexes
    }

    assert {
        "idx_candidates_application_stage",
        "idx_draft_revisions_active",
        "idx_draft_revisions_history",
        "idx_logical_send_operations_unfinalized",
        "idx_provider_attempts_operation_attempt",
        "idx_audit_logs_application_created",
    }.issubset(index_names)


def test_application_id_is_globally_unique(db: Session) -> None:
    db.add_all([make_candidate(), make_candidate()])

    with pytest.raises(IntegrityError):
        db.commit()


def test_correction_requires_meaningful_rationale(db: Session) -> None:
    candidate = make_candidate()
    draft = make_draft(candidate)
    draft.is_correction = True
    draft.correction_rationale = "no"
    db.add(draft)

    with pytest.raises(IntegrityError):
        db.commit()


def test_draft_has_at_most_one_logical_send_operation(db: Session) -> None:
    draft = make_draft(make_candidate())
    db.add_all(
        [
            LogicalSendOperation(draft_revision=draft),
            LogicalSendOperation(draft_revision=draft),
        ]
    )

    with pytest.raises(IntegrityError):
        db.commit()


def test_attempt_number_is_unique_per_operation(db: Session) -> None:
    operation = LogicalSendOperation(draft_revision=make_draft(make_candidate()))
    db.add_all(
        [
            ProviderAttempt(
                operation=operation,
                attempt_number=1,
                request_payload_digest="a" * 64,
            ),
            ProviderAttempt(
                operation=operation,
                attempt_number=1,
                request_payload_digest="a" * 64,
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        db.commit()


def test_demo_seed_candidates_satisfy_target_candidate_contract(db: Session) -> None:
    seed_candidates(db)
    candidates = db.query(Candidate).all()

    assert len(candidates) == 15
    assert len({candidate.application_id for candidate in candidates}) == 15
    assert all(candidate.email for candidate in candidates)
    assert {candidate.stage for candidate in candidates} <= {"CV_SCREENING", "INTERVIEW"}
    assert {candidate.status for candidate in candidates} <= {
        "PENDING",
        "PASS_CV",
        "REJECT_CV",
        "PASS_INTERVIEW",
        "REJECT_INTERVIEW",
    }
