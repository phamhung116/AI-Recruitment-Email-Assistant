"""Pure deterministic validation for one candidate and one rendered draft."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.templates import (
    DECISION_CRITICAL_MARKER,
    STAGE_DECISION_TEMPLATE_POLICY,
)
from app.models import Candidate
from app.schemas.validation import IssueSeverity, ValidationIssue, ValidationResult
from app.services.template_service import (
    TemplateRenderContext,
    TemplateServiceError,
    assemble_rendered_body,
    render_template,
    select_template,
)


EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PLACEHOLDER_PATTERN = re.compile(r"{{([a-zA-Z0-9_]+)}}")
GREETING_PATTERN = re.compile(
    r"^\s*(?:dear|hello|hi)\s+([^,\n:!]+)",
    re.IGNORECASE,
)
REJECTION_SUBJECT_TERMS = (
    re.compile(r"\boffer\b", re.IGNORECASE),
    re.compile(r"\bcongratulations?\b", re.IGNORECASE),
)
POSITIVE_SUBJECT_TERMS = (
    re.compile(r"\breject(?:ed|ion)?\b", re.IGNORECASE),
    re.compile(r"\bnot\s+move\s+forward\b", re.IGNORECASE),
    re.compile(r"\bunsuccessful\b", re.IGNORECASE),
)


@dataclass(frozen=True, slots=True)
class CandidateSafetyFacts:
    application_id: str | None
    full_name: str | None
    email: str | None
    stage: str | None
    status: str | None


@dataclass(frozen=True, slots=True)
class DraftSafetyData:
    application_id: str | None
    stage: str | None
    decision: str | None
    recipient: str | None
    email_type: str | None
    subject: str | None
    decision_critical_content: str | None
    editable_content: str | None
    rendered_body: str | None
    is_correction: bool = False


class ContradictionWorkflow(str, Enum):
    """Business workflow requesting an Application ID + Stage evaluation."""

    NORMAL = "normal"
    CORRECTION = "correction"


def evaluate_application_contradiction(
    db: Session,
    *,
    application_id: str | None,
    proposed_stage: str | None,
    proposed_decision: str | None,
    workflow: ContradictionWorkflow = ContradictionWorkflow.NORMAL,
    lock_for_update: bool = True,
) -> ValidationResult:
    """Load one application and evaluate its communicated outcome.

    The optional row lock lets draft/send callers keep the guard and their write in
    one transaction. This function deliberately does not commit or roll back.
    """

    normalized_application_id = (application_id or "").strip()
    if not normalized_application_id:
        return ValidationResult.from_issues(
            [
                _issue(
                    "APPLICATION_ID_REQUIRED",
                    IssueSeverity.BLOCKER,
                    "Application ID is required before checking prior communication.",
                    {"field": "application_id"},
                    "Select a valid application before creating or sending a draft.",
                )
            ]
        )

    statement = select(Candidate).where(
        Candidate.application_id == normalized_application_id
    )
    if lock_for_update:
        statement = statement.with_for_update()
    candidate = db.execute(statement).scalar_one_or_none()
    if candidate is None:
        return ValidationResult.from_issues(
            [
                _issue(
                    "APPLICATION_NOT_FOUND",
                    IssueSeverity.BLOCKER,
                    "The selected application no longer exists.",
                    {"application_id": normalized_application_id},
                    "Refresh the application list and select an existing application.",
                )
            ]
        )

    return evaluate_communication_contradiction(
        candidate,
        proposed_stage=proposed_stage,
        proposed_decision=proposed_decision,
        workflow=workflow,
    )


def evaluate_communication_contradiction(
    candidate: Candidate,
    *,
    proposed_stage: str | None,
    proposed_decision: str | None,
    workflow: ContradictionWorkflow = ContradictionWorkflow.NORMAL,
) -> ValidationResult:
    """Evaluate the approved contradiction boundary without database side effects."""

    stage = (proposed_stage or "").strip().upper()
    decision = (proposed_decision or "").strip().upper()
    issues: list[ValidationIssue] = []

    try:
        normalized_workflow = ContradictionWorkflow(workflow)
    except ValueError:
        return ValidationResult.from_issues(
            [
                _issue(
                    "CONTRADICTION_WORKFLOW_UNSUPPORTED",
                    IssueSeverity.BLOCKER,
                    "The requested contradiction workflow is not supported.",
                    {},
                    "Use the normal or decision-correction workflow.",
                )
            ]
        )

    if not stage or not decision:
        missing_fields = [
            field
            for field, value in (("stage", stage), ("decision", decision))
            if not value
        ]
        issues.append(
            _issue(
                "PROPOSED_OUTCOME_REQUIRED",
                IssueSeverity.BLOCKER,
                "Stage and hiring decision are required for contradiction checks.",
                {"missing_fields": missing_fields},
                "Choose a supported stage and hiring decision before continuing.",
            )
        )
        return ValidationResult.from_issues(issues)

    if decision == "PENDING":
        issues.append(
            _issue(
                "STATUS_PENDING",
                IssueSeverity.BLOCKER,
                "A pending application does not have a sendable outcome.",
                {"stage": stage, "decision": decision},
                "Record a hiring decision before creating an outcome email.",
            )
        )
        return ValidationResult.from_issues(issues)

    if (stage, decision) not in STAGE_DECISION_TEMPLATE_POLICY:
        issues.append(
            _issue(
                "STATUS_UNSUPPORTED",
                IssueSeverity.BLOCKER,
                "The proposed decision is not supported for this hiring stage.",
                {"stage": stage, "decision": decision},
                "Use an approved Stage and Decision combination.",
            )
        )
        return ValidationResult.from_issues(issues)

    communicated_stage = (candidate.communicated_stage or "").strip().upper()
    communicated_decision = (candidate.communicated_decision or "").strip().upper()
    if not communicated_stage and not communicated_decision:
        return ValidationResult.from_issues([])

    if not communicated_stage or not communicated_decision:
        issues.append(
            _issue(
                "COMMUNICATED_OUTCOME_INCOMPLETE",
                IssueSeverity.BLOCKER,
                "The prior communicated outcome record is incomplete.",
                {"application_id": candidate.application_id},
                "Resolve the application communication record before continuing.",
            )
        )
        return ValidationResult.from_issues(issues)

    if (communicated_stage, communicated_decision) not in STAGE_DECISION_TEMPLATE_POLICY:
        issues.append(
            _issue(
                "COMMUNICATED_OUTCOME_UNSUPPORTED",
                IssueSeverity.BLOCKER,
                "The prior communicated outcome is outside the approved policy.",
                {
                    "application_id": candidate.application_id,
                    "communicated_stage": communicated_stage,
                    "communicated_decision": communicated_decision,
                },
                "Resolve the application communication record before continuing.",
            )
        )
        return ValidationResult.from_issues(issues)

    is_opposing_same_stage = (
        communicated_stage == stage and communicated_decision != decision
    )
    if is_opposing_same_stage and normalized_workflow == ContradictionWorkflow.NORMAL:
        issues.append(
            _issue(
                "CONTRADICTORY_COMMUNICATED_DECISION",
                IssueSeverity.BLOCKER,
                "An opposing decision was already communicated for this application stage.",
                {
                    "application_id": candidate.application_id,
                    "stage": stage,
                    "communicated_decision": communicated_decision,
                    "proposed_decision": decision,
                },
                "Use Create decision correction to change an already communicated outcome.",
            )
        )

    return ValidationResult.from_issues(issues)


def evaluate_draft_safety(
    candidate: CandidateSafetyFacts,
    draft: DraftSafetyData,
) -> ValidationResult:
    """Run every local rule and aggregate all blocking findings."""

    issues: list[ValidationIssue] = []
    _validate_required_values(candidate, draft, issues)
    _validate_emails(candidate, draft, issues)
    _validate_locked_fields(candidate, draft, issues)
    policy_is_valid = _validate_policy(draft, issues)
    _validate_rendered_content(candidate, draft, policy_is_valid, issues)
    _validate_name_alignment(candidate, draft, issues)
    _validate_subject_alignment(draft, issues)
    return ValidationResult.from_issues(issues)


def _validate_required_values(
    candidate: CandidateSafetyFacts,
    draft: DraftSafetyData,
    issues: list[ValidationIssue],
) -> None:
    candidate_values = {
        "application_id": candidate.application_id,
        "candidate_name": candidate.full_name,
        "email": candidate.email,
        "stage": candidate.stage,
        "status": candidate.status,
    }
    missing_candidate_fields = sorted(
        name for name, value in candidate_values.items() if not _has_text(value)
    )
    if missing_candidate_fields:
        issues.append(
            _issue(
                "CANDIDATE_REQUIRED_VALUE_MISSING",
                IssueSeverity.ERROR,
                "Required candidate information is missing.",
                {"missing_fields": missing_candidate_fields},
                "Complete the verified candidate record before reviewing this draft.",
            )
        )

    draft_values = {
        "application_id": draft.application_id,
        "stage": draft.stage,
        "decision": draft.decision,
        "recipient": draft.recipient,
        "email_type": draft.email_type,
        "subject": draft.subject,
        "decision_critical_content": draft.decision_critical_content,
        "editable_content": draft.editable_content,
        "rendered_body": draft.rendered_body,
    }
    missing_draft_fields = sorted(
        name for name, value in draft_values.items() if not _has_text(value)
    )
    if missing_draft_fields:
        issues.append(
            _issue(
                "DRAFT_REQUIRED_VALUE_MISSING",
                IssueSeverity.ERROR,
                "Required draft information is missing.",
                {"missing_fields": missing_draft_fields},
                "Regenerate the draft from the verified application record.",
            )
        )


def _validate_emails(
    candidate: CandidateSafetyFacts,
    draft: DraftSafetyData,
    issues: list[ValidationIssue],
) -> None:
    if _has_text(candidate.email) and EMAIL_PATTERN.fullmatch(candidate.email.strip()) is None:
        issues.append(
            _issue(
                "CANDIDATE_EMAIL_FORMAT",
                IssueSeverity.ERROR,
                "The candidate email address has an invalid format.",
                {"field": "candidate.email"},
                "Correct the candidate email after verifying it with the candidate.",
            )
        )
    if _has_text(draft.recipient) and EMAIL_PATTERN.fullmatch(draft.recipient.strip()) is None:
        issues.append(
            _issue(
                "RECIPIENT_EMAIL_FORMAT",
                IssueSeverity.ERROR,
                "The draft recipient address has an invalid format.",
                {"field": "draft.recipient"},
                "Regenerate the draft after correcting the verified candidate email.",
            )
        )


def _validate_locked_fields(
    candidate: CandidateSafetyFacts,
    draft: DraftSafetyData,
    issues: list[ValidationIssue],
) -> None:
    mismatched_fields: list[str] = []
    if _normalized(candidate.application_id) != _normalized(draft.application_id):
        mismatched_fields.append("application_id")
    if _normalized(candidate.stage) != _normalized(draft.stage):
        mismatched_fields.append("stage")
    if _normalized(candidate.status) != _normalized(draft.decision):
        mismatched_fields.append("decision")
    if _normalized(candidate.email) != _normalized(draft.recipient):
        mismatched_fields.append("recipient")

    if mismatched_fields:
        issues.append(
            _issue(
                "LOCKED_FIELD_MISMATCH",
                IssueSeverity.BLOCKER,
                "The draft no longer matches the verified application record.",
                {"mismatched_fields": sorted(mismatched_fields)},
                "Discard this draft and regenerate it from the current application record.",
            )
        )


def _validate_policy(
    draft: DraftSafetyData,
    issues: list[ValidationIssue],
) -> bool:
    if not all(_has_text(value) for value in (draft.stage, draft.decision, draft.email_type)):
        return False

    context = _template_context_from_draft(draft, candidate_name="validated-later")
    try:
        select_template(context)
    except TemplateServiceError as error:
        issues.append(
            _issue(
                error.error_code,
                IssueSeverity.BLOCKER,
                error.message,
                {
                    "stage": draft.stage or "",
                    "decision": draft.decision or "",
                    "email_type": draft.email_type or "",
                },
                "Use the approved Stage, Decision and Email Type combination.",
            )
        )
        return False
    return True


def _validate_rendered_content(
    candidate: CandidateSafetyFacts,
    draft: DraftSafetyData,
    policy_is_valid: bool,
    issues: list[ValidationIssue],
) -> None:
    unresolved = sorted(
        set(
            PLACEHOLDER_PATTERN.findall(
                "\n".join(
                    (
                        draft.subject or "",
                        draft.decision_critical_content or "",
                        draft.rendered_body or "",
                    )
                )
            )
        )
    )
    editable_unresolved = sorted(
        placeholder
        for placeholder in set(PLACEHOLDER_PATTERN.findall(draft.editable_content or ""))
        if placeholder != "decision_critical_content"
    )
    unresolved = sorted(set(unresolved + editable_unresolved))
    if unresolved:
        issues.append(
            _issue(
                "TEMPLATE_UNRESOLVED_PLACEHOLDER",
                IssueSeverity.ERROR,
                "The draft still contains unresolved template values.",
                {"unresolved_placeholders": unresolved},
                "Regenerate the draft after completing the required candidate information.",
            )
        )

    expected_critical_content: str | None = None
    if policy_is_valid and all(
        _has_text(value)
        for value in (
            candidate.application_id,
            candidate.full_name,
            candidate.email,
            draft.stage,
            draft.decision,
            draft.email_type,
        )
    ):
        context = _template_context_from_draft(draft, candidate.full_name or "")
        try:
            expected_critical_content = render_template(context).decision_critical_content
        except TemplateServiceError as error:
            issues.append(
                _issue(
                    error.error_code,
                    IssueSeverity.ERROR,
                    error.message,
                    {},
                    "Regenerate the draft from the fixed template catalog.",
                )
            )

    if (
        expected_critical_content is not None
        and draft.decision_critical_content != expected_critical_content
    ):
        issues.append(
            _issue(
                "DECISION_CRITICAL_CONTENT_MODIFIED",
                IssueSeverity.BLOCKER,
                "Decision-critical content does not match the fixed template.",
                {"field": "decision_critical_content"},
                "Discard the edited outcome text and regenerate the draft.",
            )
        )

    assembled_body: str | None = None
    if _has_text(draft.editable_content) and _has_text(draft.decision_critical_content):
        try:
            assembled_body = assemble_rendered_body(
                draft.decision_critical_content or "",
                draft.editable_content or "",
            )
        except TemplateServiceError as error:
            issues.append(
                _issue(
                    error.error_code,
                    IssueSeverity.BLOCKER,
                    error.message,
                    {"field": "editable_content"},
                    "Restore the protected content insertion point or regenerate the draft.",
                )
            )

    if assembled_body is not None and assembled_body != (draft.rendered_body or ""):
        issues.append(
            _issue(
                "RENDERED_BODY_MISMATCH",
                IssueSeverity.BLOCKER,
                "The rendered body does not match its protected and editable source sections.",
                {"field": "rendered_body"},
                "Regenerate the body from the saved draft sections.",
            )
        )
    if (
        _has_text(draft.decision_critical_content)
        and (draft.rendered_body or "").count(draft.decision_critical_content or "") != 1
    ):
        issues.append(
            _issue(
                "DECISION_CRITICAL_CONTENT_COUNT_INVALID",
                IssueSeverity.BLOCKER,
                "The rendered email must contain the protected outcome exactly once.",
                {"expected_occurrences": 1},
                "Regenerate the body from the fixed template and editable content.",
            )
        )


def _validate_name_alignment(
    candidate: CandidateSafetyFacts,
    draft: DraftSafetyData,
    issues: list[ValidationIssue],
) -> None:
    if not _has_text(candidate.full_name) or not _has_text(draft.rendered_body):
        return

    first_line = next(
        (line.strip() for line in (draft.rendered_body or "").splitlines() if line.strip()),
        "",
    )
    match = GREETING_PATTERN.match(first_line)
    if match is None:
        issues.append(
            _issue(
                "CANDIDATE_NAME_MISSING_FROM_DRAFT",
                IssueSeverity.ERROR,
                "The email greeting does not identify the selected candidate.",
                {"location": "body_greeting"},
                "Add the verified candidate name to the greeting.",
            )
        )
        return

    detected_name = _normalized(match.group(1))
    if detected_name != _normalized(candidate.full_name):
        issues.append(
            _issue(
                "CANDIDATE_NAME_MISMATCH",
                IssueSeverity.BLOCKER,
                "The name in the email greeting does not match the selected candidate.",
                {"location": "body_greeting"},
                "Replace the greeting name with the verified candidate name.",
            )
        )


def _validate_subject_alignment(
    draft: DraftSafetyData,
    issues: list[ValidationIssue],
) -> None:
    if not _has_text(draft.subject) or not _has_text(draft.decision):
        return

    patterns = (
        REJECTION_SUBJECT_TERMS
        if draft.decision in {"REJECT_CV", "REJECT_INTERVIEW"}
        else POSITIVE_SUBJECT_TERMS
        if draft.decision in {"PASS_CV", "PASS_INTERVIEW"}
        else ()
    )
    if any(pattern.search(draft.subject or "") for pattern in patterns):
        issues.append(
            _issue(
                "STATUS_EMAIL_MISMATCH",
                IssueSeverity.BLOCKER,
                "The email subject suggests an outcome that conflicts with the hiring decision.",
                {"field": "subject", "decision": draft.decision},
                "Use a neutral subject or wording aligned with the verified decision.",
            )
        )


def _template_context_from_draft(
    draft: DraftSafetyData,
    candidate_name: str,
) -> TemplateRenderContext:
    return TemplateRenderContext(
        application_id=draft.application_id or "",
        candidate_name=candidate_name,
        recipient=draft.recipient or "",
        stage=draft.stage or "",
        decision=draft.decision or "",
        email_type=draft.email_type or "",
        is_correction=draft.is_correction,
    )


def _has_text(value: str | None) -> bool:
    return bool(value and value.strip())


def _normalized(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _issue(
    rule_id: str,
    severity: IssueSeverity,
    message: str,
    evidence: dict[str, Any],
    remediation: str,
) -> ValidationIssue:
    return ValidationIssue(
        rule_id=rule_id,
        severity=severity,
        message=message,
        evidence=evidence,
        remediation=remediation,
        is_blocking=True,
    )
