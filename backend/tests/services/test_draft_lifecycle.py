from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.constants.templates import DECISION_CRITICAL_MARKER, INTERVIEW_INVITATION
from app.db.database import Base, build_engine
from app.models import Candidate, DraftRevision, DraftStatus
from app.services.draft_service import DraftServiceError, generate_draft, revise_draft
from app.services.template_service import TemplateServiceError


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


def add_candidate(
    db: Session,
    *,
    stage: str = "CV_SCREENING",
    status: str = "PASS_CV",
    communicated_stage: str | None = None,
    communicated_decision: str | None = None,
) -> Candidate:
    candidate = Candidate(
        id=1,
        application_id="APP-2026-001",
        full_name="Nguyen Van A",
        email="Candidate@Example.com",
        stage=stage,
        status=status,
        communicated_stage=communicated_stage,
        communicated_decision=communicated_decision,
    )
    db.add(candidate)
    db.commit()
    return candidate


def count_drafts(db: Session) -> int:
    return db.execute(select(func.count()).select_from(DraftRevision)).scalar_one()


def test_generate_draft_renders_valid_revision_and_guard_evidence(db: Session) -> None:
    add_candidate(db)

    draft = generate_draft(db, application_id="APP-2026-001", actor="hr.one")

    assert draft.revision_number == 1
    assert draft.template_code == INTERVIEW_INVITATION
    assert draft.to_email == "candidate@example.com"
    assert draft.status == DraftStatus.READY_TO_SEND.value
    assert draft.created_by == "hr.one"
    assert draft.risk_check_result["passed"] is True
    assert draft.risk_check_result["issues"] == []
    assert DECISION_CRITICAL_MARKER in draft.editable_content
    assert draft.decision_critical_content in draft.rendered_body


def test_generate_draft_rejects_missing_unknown_and_pending_application(
    db: Session,
) -> None:
    add_candidate(db, status="PENDING")

    with pytest.raises(DraftServiceError) as missing:
        generate_draft(db, application_id=" ")
    with pytest.raises(DraftServiceError) as unknown:
        generate_draft(db, application_id="APP-UNKNOWN")
    with pytest.raises(TemplateServiceError) as pending:
        generate_draft(db, application_id="APP-2026-001")

    assert missing.value.error_code == "APPLICATION_ID_REQUIRED"
    assert unknown.value.error_code == "APPLICATION_NOT_FOUND"
    assert pending.value.error_code == "STATUS_PENDING"
    assert count_drafts(db) == 0


def test_contradiction_creates_blocked_revision_with_human_guidance(db: Session) -> None:
    add_candidate(
        db,
        status="REJECT_CV",
        communicated_stage="CV_SCREENING",
        communicated_decision="PASS_CV",
    )

    draft = generate_draft(db, application_id="APP-2026-001")

    assert draft.status == DraftStatus.BLOCKED_DETERMINISTIC.value
    assert draft.risk_check_result["passed"] is False
    issue = draft.risk_check_result["issues"][0]
    assert issue["rule_id"] == "CONTRADICTORY_COMMUNICATED_DECISION"
    assert "Create decision correction" in issue["remediation"]


def test_new_same_stage_revision_supersedes_older_unsent_revision(db: Session) -> None:
    add_candidate(db)
    first = generate_draft(db, application_id="APP-2026-001")
    db.flush()

    second = generate_draft(db, application_id="APP-2026-001")

    assert second.revision_number == 2
    assert second.status == DraftStatus.READY_TO_SEND.value
    assert first.status == DraftStatus.SUPERSEDED.value
    assert first.superseded_at is not None


def test_revision_numbers_are_candidate_wide_but_superseding_is_stage_scoped(
    db: Session,
) -> None:
    candidate = add_candidate(db)
    cv_draft = generate_draft(db, application_id="APP-2026-001")
    candidate.stage = "INTERVIEW"
    candidate.status = "REJECT_INTERVIEW"
    db.flush()

    interview_draft = generate_draft(db, application_id="APP-2026-001")

    assert interview_draft.revision_number == 2
    assert interview_draft.stage == "INTERVIEW"
    assert cv_draft.status == DraftStatus.READY_TO_SEND.value
    assert cv_draft.superseded_at is None


def test_edit_creates_new_revision_and_supersedes_source(db: Session) -> None:
    add_candidate(db)
    source = generate_draft(db, application_id="APP-2026-001")
    revised_content = source.editable_content.replace(
        "Please contact our recruitment team if you need any clarification.",
        "Please reply if you would like to discuss the interview schedule.",
    )

    revised = revise_draft(
        db,
        draft_revision_id=source.id,
        editable_content=revised_content,
        actor="hr.editor",
    )

    assert revised.id != source.id
    assert revised.revision_number == 2
    assert revised.status == DraftStatus.READY_TO_SEND.value
    assert revised.created_by == "hr.editor"
    assert "interview schedule" in revised.rendered_body
    assert source.status == DraftStatus.SUPERSEDED.value


def test_subject_edit_rechecks_guard_and_can_be_fixed_in_next_revision(db: Session) -> None:
    add_candidate(db)
    source = generate_draft(db, application_id="APP-2026-001")

    blocked = revise_draft(
        db,
        draft_revision_id=source.id,
        subject="Rejection notice",
    )
    fixed = revise_draft(
        db,
        draft_revision_id=blocked.id,
        subject="Application update",
    )

    assert blocked.status == DraftStatus.SUPERSEDED.value
    assert blocked.risk_check_result["passed"] is False
    assert blocked.risk_check_result["issues"][0]["rule_id"] == "STATUS_EMAIL_MISMATCH"
    assert fixed.revision_number == 3
    assert fixed.status == DraftStatus.READY_TO_SEND.value


def test_no_op_edit_returns_source_without_creating_revision(db: Session) -> None:
    add_candidate(db)
    source = generate_draft(db, application_id="APP-2026-001")

    returned = revise_draft(
        db,
        draft_revision_id=source.id,
        editable_content=source.editable_content,
        subject=source.subject,
    )

    assert returned is source
    assert count_drafts(db) == 1
    assert source.status == DraftStatus.READY_TO_SEND.value


def test_edit_cannot_remove_protected_content_marker(db: Session) -> None:
    add_candidate(db)
    source = generate_draft(db, application_id="APP-2026-001")

    with pytest.raises(TemplateServiceError) as error:
        revise_draft(
            db,
            draft_revision_id=source.id,
            editable_content="Dear Nguyen Van A,\n\nNo protected outcome here.",
        )

    assert error.value.error_code == "DECISION_CRITICAL_CONTENT_MODIFIED"
    assert source.status == DraftStatus.READY_TO_SEND.value
    assert count_drafts(db) == 1


@pytest.mark.parametrize(
    ("status", "expected_code"),
    [
        (DraftStatus.SUPERSEDED.value, "DRAFT_REVISION_STALE"),
        (DraftStatus.FROZEN_IN_FLIGHT.value, "DRAFT_FROZEN_IN_FLIGHT"),
        (DraftStatus.FINALIZED.value, "DRAFT_NOT_EDITABLE"),
        (DraftStatus.DISCARDED.value, "DRAFT_NOT_EDITABLE"),
    ],
)
def test_non_editable_revision_states_are_rejected(
    db: Session,
    status: str,
    expected_code: str,
) -> None:
    add_candidate(db)
    source = generate_draft(db, application_id="APP-2026-001")
    source.status = status
    db.flush()

    with pytest.raises(DraftServiceError) as error:
        revise_draft(db, draft_revision_id=source.id, subject="Changed")

    assert error.value.error_code == expected_code


def test_normal_edit_rejects_correction_draft(db: Session) -> None:
    add_candidate(db)
    source = generate_draft(db, application_id="APP-2026-001")
    source.is_correction = True
    source.status = DraftStatus.CORRECTION_DRAFT.value
    source.correction_rationale = "Decision changed after review"
    db.flush()

    with pytest.raises(DraftServiceError) as error:
        revise_draft(db, draft_revision_id=source.id, subject="Changed")

    assert error.value.error_code == "CORRECTION_WORKFLOW_REQUIRED"


def test_frozen_draft_blocks_new_generation_for_same_stage(db: Session) -> None:
    add_candidate(db)
    source = generate_draft(db, application_id="APP-2026-001")
    source.status = DraftStatus.FROZEN_IN_FLIGHT.value
    db.flush()

    with pytest.raises(DraftServiceError) as error:
        generate_draft(db, application_id="APP-2026-001")

    assert error.value.error_code == "DRAFT_FROZEN_IN_FLIGHT"
    assert count_drafts(db) == 1


def test_editing_non_latest_active_revision_is_rejected(db: Session) -> None:
    add_candidate(db)
    older = generate_draft(db, application_id="APP-2026-001")
    newer = generate_draft(db, application_id="APP-2026-001")
    older.status = DraftStatus.READY_TO_SEND.value
    db.flush()

    with pytest.raises(DraftServiceError) as error:
        revise_draft(db, draft_revision_id=older.id, subject="Changed")

    assert newer.status == DraftStatus.READY_TO_SEND.value
    assert error.value.error_code == "DRAFT_REVISION_STALE"


def test_service_does_not_commit_callers_transaction(db: Session) -> None:
    add_candidate(db)

    draft = generate_draft(db, application_id="APP-2026-001")
    db.rollback()

    assert draft.revision_number == 1
    assert count_drafts(db) == 0

