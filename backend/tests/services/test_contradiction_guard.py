from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base, build_engine
from app.models import Candidate
from app.schemas.validation import ValidationResult
from app.services.safety_guard import (
    ContradictionWorkflow,
    evaluate_application_contradiction,
    evaluate_communication_contradiction,
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


def candidate(
    *,
    identifier: int = 1,
    application_id: str = "APP-2026-001",
    stage: str = "CV_SCREENING",
    status: str = "PASS_CV",
    communicated_stage: str | None = None,
    communicated_decision: str | None = None,
) -> Candidate:
    return Candidate(
        id=identifier,
        application_id=application_id,
        full_name="Nguyen Van A",
        email="candidate@example.com",
        stage=stage,
        status=status,
        communicated_stage=communicated_stage,
        communicated_decision=communicated_decision,
    )


def issue_ids(result: ValidationResult) -> list[str]:
    return [issue.rule_id for issue in result.issues]


def test_missing_application_id_and_unknown_application_fail_closed(db: Session) -> None:
    missing = evaluate_application_contradiction(
        db,
        application_id=" ",
        proposed_stage="CV_SCREENING",
        proposed_decision="PASS_CV",
    )
    unknown = evaluate_application_contradiction(
        db,
        application_id="APP-NOT-FOUND",
        proposed_stage="CV_SCREENING",
        proposed_decision="PASS_CV",
    )

    assert issue_ids(missing) == ["APPLICATION_ID_REQUIRED"]
    assert issue_ids(unknown) == ["APPLICATION_NOT_FOUND"]


def test_application_without_communicated_outcome_passes(db: Session) -> None:
    db.add(candidate())
    db.commit()

    result = evaluate_application_contradiction(
        db,
        application_id="APP-2026-001",
        proposed_stage="CV_SCREENING",
        proposed_decision="PASS_CV",
    )

    assert result.passed is True
    assert result.issues == []


def test_database_guard_does_not_commit_callers_transaction(db: Session) -> None:
    db.add(candidate())

    result = evaluate_application_contradiction(
        db,
        application_id="APP-2026-001",
        proposed_stage="CV_SCREENING",
        proposed_decision="PASS_CV",
    )
    db.rollback()

    assert result.passed is True
    assert db.execute(select(Candidate)).scalars().all() == []


def test_same_stage_same_decision_is_not_an_opposing_contradiction() -> None:
    existing = candidate(
        communicated_stage="CV_SCREENING",
        communicated_decision="PASS_CV",
    )

    result = evaluate_communication_contradiction(
        existing,
        proposed_stage="CV_SCREENING",
        proposed_decision="PASS_CV",
    )

    assert result.passed is True


def test_normal_workflow_blocks_opposing_decision_in_same_stage() -> None:
    existing = candidate(
        communicated_stage="CV_SCREENING",
        communicated_decision="PASS_CV",
    )

    result = evaluate_communication_contradiction(
        existing,
        proposed_stage="CV_SCREENING",
        proposed_decision="REJECT_CV",
    )

    assert result.passed is False
    assert issue_ids(result) == ["CONTRADICTORY_COMMUNICATED_DECISION"]
    issue = result.issues[0]
    assert issue.evidence == {
        "application_id": "APP-2026-001",
        "stage": "CV_SCREENING",
        "communicated_decision": "PASS_CV",
        "proposed_decision": "REJECT_CV",
    }
    assert "Create decision correction" in issue.remediation


def test_valid_cross_stage_progression_is_not_blocked() -> None:
    existing = candidate(
        stage="INTERVIEW",
        status="REJECT_INTERVIEW",
        communicated_stage="CV_SCREENING",
        communicated_decision="PASS_CV",
    )

    result = evaluate_communication_contradiction(
        existing,
        proposed_stage="INTERVIEW",
        proposed_decision="REJECT_INTERVIEW",
    )

    assert result.passed is True


def test_other_application_does_not_affect_selected_application(db: Session) -> None:
    db.add_all(
        [
            candidate(
                identifier=1,
                application_id="APP-OTHER",
                communicated_stage="CV_SCREENING",
                communicated_decision="PASS_CV",
            ),
            candidate(identifier=2, application_id="APP-TARGET"),
        ]
    )
    db.commit()

    result = evaluate_application_contradiction(
        db,
        application_id="APP-TARGET",
        proposed_stage="CV_SCREENING",
        proposed_decision="REJECT_CV",
    )

    assert result.passed is True


def test_correction_workflow_can_change_same_stage_decision() -> None:
    existing = candidate(
        communicated_stage="INTERVIEW",
        communicated_decision="PASS_INTERVIEW",
    )

    result = evaluate_communication_contradiction(
        existing,
        proposed_stage="INTERVIEW",
        proposed_decision="REJECT_INTERVIEW",
        workflow=ContradictionWorkflow.CORRECTION,
    )

    assert result.passed is True


def test_unknown_workflow_cannot_bypass_contradiction_guard() -> None:
    existing = candidate(
        communicated_stage="INTERVIEW",
        communicated_decision="PASS_INTERVIEW",
    )

    result = evaluate_communication_contradiction(
        existing,
        proposed_stage="INTERVIEW",
        proposed_decision="REJECT_INTERVIEW",
        workflow="unknown",  # type: ignore[arg-type]
    )

    assert issue_ids(result) == ["CONTRADICTION_WORKFLOW_UNSUPPORTED"]


@pytest.mark.parametrize(
    ("stage", "decision", "expected_rule"),
    [
        ("", "", "PROPOSED_OUTCOME_REQUIRED"),
        ("CV_SCREENING", "PENDING", "STATUS_PENDING"),
        ("CV_SCREENING", "PASS_INTERVIEW", "STATUS_UNSUPPORTED"),
        ("UNKNOWN", "PASS_CV", "STATUS_UNSUPPORTED"),
    ],
)
def test_invalid_proposed_outcome_fails_closed(
    stage: str,
    decision: str,
    expected_rule: str,
) -> None:
    result = evaluate_communication_contradiction(
        candidate(),
        proposed_stage=stage,
        proposed_decision=decision,
    )

    assert issue_ids(result) == [expected_rule]


def test_incomplete_or_unsupported_communicated_outcome_fails_closed() -> None:
    incomplete = evaluate_communication_contradiction(
        candidate(communicated_stage="CV_SCREENING"),
        proposed_stage="CV_SCREENING",
        proposed_decision="PASS_CV",
    )
    unsupported = evaluate_communication_contradiction(
        candidate(
            communicated_stage="CV_SCREENING",
            communicated_decision="PASS_INTERVIEW",
        ),
        proposed_stage="CV_SCREENING",
        proposed_decision="PASS_CV",
    )

    assert issue_ids(incomplete) == ["COMMUNICATED_OUTCOME_INCOMPLETE"]
    assert issue_ids(unsupported) == ["COMMUNICATED_OUTCOME_UNSUPPORTED"]


def test_contradiction_evidence_does_not_include_candidate_name_or_email() -> None:
    existing = candidate(
        communicated_stage="CV_SCREENING",
        communicated_decision="REJECT_CV",
    )

    result = evaluate_communication_contradiction(
        existing,
        proposed_stage="CV_SCREENING",
        proposed_decision="PASS_CV",
    )
    evidence = str(result.issues[0].evidence)

    assert existing.full_name not in evidence
    assert existing.email not in evidence
