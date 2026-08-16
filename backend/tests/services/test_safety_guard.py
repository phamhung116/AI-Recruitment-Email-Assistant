from __future__ import annotations

from dataclasses import replace

import pytest

from app.constants.templates import (
    DECISION_CRITICAL_MARKER,
    INTERVIEW_INVITATION,
    OFFER_EMAIL,
    REJECTION_AFTER_CV,
    REJECTION_AFTER_INTERVIEW,
)
from app.services.safety_guard import (
    CandidateSafetyFacts,
    DraftSafetyData,
    evaluate_draft_safety,
)
from app.services.template_service import TemplateRenderContext, render_template


def valid_pair(
    *,
    stage: str = "CV_SCREENING",
    decision: str = "PASS_CV",
    email_type: str = INTERVIEW_INVITATION,
) -> tuple[CandidateSafetyFacts, DraftSafetyData]:
    candidate = CandidateSafetyFacts(
        application_id="APP-2026-001",
        full_name="Nguyen Van A",
        email="candidate@example.com",
        stage=stage,
        status=decision,
    )
    context = TemplateRenderContext(
        application_id=candidate.application_id,
        candidate_name=candidate.full_name,
        recipient=candidate.email,
        stage=stage,
        decision=decision,
        email_type=email_type,
    )
    rendered = render_template(context)
    draft = DraftSafetyData(
        application_id=candidate.application_id,
        stage=stage,
        decision=decision,
        recipient=candidate.email,
        email_type=email_type,
        subject=rendered.subject,
        decision_critical_content=rendered.decision_critical_content,
        editable_content=rendered.editable_content,
        rendered_body=rendered.rendered_body,
    )
    return candidate, draft


def issue_ids(candidate: CandidateSafetyFacts, draft: DraftSafetyData) -> list[str]:
    return [
        issue.rule_id
        for issue in evaluate_draft_safety(candidate, draft).issues
    ]


@pytest.mark.parametrize(
    ("stage", "decision", "email_type"),
    [
        ("CV_SCREENING", "PASS_CV", INTERVIEW_INVITATION),
        ("CV_SCREENING", "REJECT_CV", REJECTION_AFTER_CV),
        ("INTERVIEW", "PASS_INTERVIEW", OFFER_EMAIL),
        ("INTERVIEW", "REJECT_INTERVIEW", REJECTION_AFTER_INTERVIEW),
    ],
)
def test_every_approved_policy_draft_passes(
    stage: str,
    decision: str,
    email_type: str,
) -> None:
    candidate, draft = valid_pair(
        stage=stage,
        decision=decision,
        email_type=email_type,
    )

    result = evaluate_draft_safety(candidate, draft)

    assert result.passed is True
    assert result.issues == []


def test_missing_candidate_and_draft_values_are_aggregated() -> None:
    candidate, draft = valid_pair()
    candidate = replace(candidate, application_id="", full_name="", email="")
    draft = replace(draft, subject="", rendered_body="")

    result = evaluate_draft_safety(candidate, draft)

    assert result.passed is False
    assert "CANDIDATE_REQUIRED_VALUE_MISSING" in issue_ids(candidate, draft)
    assert "DRAFT_REQUIRED_VALUE_MISSING" in issue_ids(candidate, draft)
    candidate_issue = next(
        issue
        for issue in result.issues
        if issue.rule_id == "CANDIDATE_REQUIRED_VALUE_MISSING"
    )
    assert candidate_issue.evidence == {
        "missing_fields": ["application_id", "candidate_name", "email"]
    }


def test_null_values_fail_closed_without_crashing() -> None:
    candidate, draft = valid_pair()
    candidate = replace(candidate, email=None, stage=None)
    draft = replace(draft, recipient=None, stage=None, rendered_body=None)

    result = evaluate_draft_safety(candidate, draft)

    assert result.passed is False
    assert "CANDIDATE_REQUIRED_VALUE_MISSING" in [
        issue.rule_id for issue in result.issues
    ]
    assert "DRAFT_REQUIRED_VALUE_MISSING" in [issue.rule_id for issue in result.issues]


def test_candidate_and_recipient_email_formats_are_both_checked() -> None:
    candidate, draft = valid_pair()
    candidate = replace(candidate, email="bad-candidate-email")
    draft = replace(draft, recipient="bad-recipient-email")

    ids = issue_ids(candidate, draft)

    assert "CANDIDATE_EMAIL_FORMAT" in ids
    assert "RECIPIENT_EMAIL_FORMAT" in ids


def test_locked_application_fields_must_match_candidate_facts() -> None:
    candidate, draft = valid_pair()
    draft = replace(
        draft,
        application_id="APP-WRONG",
        stage="INTERVIEW",
        decision="PASS_INTERVIEW",
        recipient="other@example.com",
        email_type=OFFER_EMAIL,
    )

    result = evaluate_draft_safety(candidate, draft)
    locked_issue = next(
        issue for issue in result.issues if issue.rule_id == "LOCKED_FIELD_MISMATCH"
    )

    assert locked_issue.evidence == {
        "mismatched_fields": ["application_id", "decision", "recipient", "stage"]
    }


def test_pending_and_email_type_mismatch_fail_closed() -> None:
    candidate, draft = valid_pair()
    pending_candidate = replace(candidate, status="PENDING")
    pending_draft = replace(draft, decision="PENDING")

    assert "STATUS_PENDING" in issue_ids(pending_candidate, pending_draft)
    assert "STATUS_EMAIL_MISMATCH" in issue_ids(
        candidate,
        replace(draft, email_type=REJECTION_AFTER_CV),
    )


def test_modified_decision_critical_content_is_blocked() -> None:
    candidate, draft = valid_pair()
    modified_text = "We will not move forward with your application."
    modified_draft = replace(
        draft,
        decision_critical_content=modified_text,
        rendered_body=draft.rendered_body.replace(
            draft.decision_critical_content,
            modified_text,
        ),
    )

    ids = issue_ids(candidate, modified_draft)

    assert "DECISION_CRITICAL_CONTENT_MODIFIED" in ids


@pytest.mark.parametrize(
    "editable_content",
    [
        "Dear Nguyen Van A,\n\nNo protected insertion point.",
        f"Dear Nguyen Van A,\n\n{DECISION_CRITICAL_MARKER}\n{DECISION_CRITICAL_MARKER}",
    ],
)
def test_protected_insertion_point_cannot_be_removed_or_duplicated(
    editable_content: str,
) -> None:
    candidate, draft = valid_pair()

    assert "DECISION_CRITICAL_CONTENT_MODIFIED" in issue_ids(
        candidate,
        replace(draft, editable_content=editable_content),
    )


def test_rendered_body_must_match_saved_sections() -> None:
    candidate, draft = valid_pair()

    ids = issue_ids(
        candidate,
        replace(draft, rendered_body=draft.rendered_body + "\nUntracked change"),
    )

    assert "RENDERED_BODY_MISMATCH" in ids


def test_unresolved_placeholders_are_reported() -> None:
    candidate, draft = valid_pair()
    draft = replace(
        draft,
        subject="Application update {{unknown_value}}",
    )

    result = evaluate_draft_safety(candidate, draft)
    issue = next(
        item
        for item in result.issues
        if item.rule_id == "TEMPLATE_UNRESOLVED_PLACEHOLDER"
    )

    assert issue.evidence == {"unresolved_placeholders": ["unknown_value"]}


def test_candidate_name_mismatch_and_missing_greeting_are_blocking() -> None:
    candidate, draft = valid_pair()
    wrong_name = replace(
        draft,
        editable_content=draft.editable_content.replace("Nguyen Van A", "Tran Van B"),
        rendered_body=draft.rendered_body.replace("Nguyen Van A", "Tran Van B"),
    )
    no_greeting = replace(
        draft,
        editable_content=draft.editable_content.replace("Dear Nguyen Van A,\n\n", ""),
        rendered_body=draft.rendered_body.replace("Dear Nguyen Van A,\n\n", ""),
    )

    assert "CANDIDATE_NAME_MISMATCH" in issue_ids(candidate, wrong_name)
    assert "CANDIDATE_NAME_MISSING_FROM_DRAFT" in issue_ids(candidate, no_greeting)


@pytest.mark.parametrize("subject", ["Offer for you", "Congratulations on your result"])
def test_rejection_draft_blocks_positive_subject_terms(subject: str) -> None:
    candidate, draft = valid_pair(
        stage="CV_SCREENING",
        decision="REJECT_CV",
        email_type=REJECTION_AFTER_CV,
    )

    assert "STATUS_EMAIL_MISMATCH" in issue_ids(
        candidate,
        replace(draft, subject=subject),
    )


@pytest.mark.parametrize("subject", ["Rejection notice", "We will not move forward"])
def test_positive_draft_blocks_rejection_subject_terms(subject: str) -> None:
    candidate, draft = valid_pair()

    assert "STATUS_EMAIL_MISMATCH" in issue_ids(
        candidate,
        replace(draft, subject=subject),
    )


def test_issue_evidence_does_not_repeat_candidate_pii() -> None:
    candidate, draft = valid_pair()
    result = evaluate_draft_safety(
        candidate,
        replace(draft, recipient="other@example.com", rendered_body="Hello Wrong Person"),
    )
    evidence_text = " ".join(str(issue.evidence) for issue in result.issues)

    assert candidate.full_name not in evidence_text
    assert candidate.email not in evidence_text
