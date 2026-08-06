import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import Candidate, EmailHistory, EmailTemplate
from app.schemas.validation import IssueSeverity, ValidationIssue, ValidationResult
from app.services.rules import SENSITIVE_EMAIL_TYPES, STATUS_EMAIL_RULES, email_type_for_status


PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GREETING_NAME_RE = re.compile(
    r"^\s*(?:dear|hello|hi|xin\s+chào|chào)\s+([^,\n:!]+)",
    re.IGNORECASE,
)
NAME_PLACEHOLDERS = {"candidate_name", "full_name"}
SUPPORTED_PLACEHOLDERS = {
    "candidate_name",
    "email",
    "email_type",
    "full_name",
    "interview_time",
    "interviewer",
    "note",
    "phone",
    "position",
    "stage",
    "status",
}


def validate_email_draft(
    db: Session,
    candidate: Candidate,
    template: EmailTemplate | None,
    email_type: str,
    rendered_subject: str | None = None,
    rendered_body: str | None = None,
) -> ValidationResult:
    issues: list[ValidationIssue] = []
    _validate_candidate(candidate, issues)
    _validate_status_mapping(candidate, email_type, issues)
    _validate_template(candidate, template, email_type, issues)
    _validate_rendered_draft(candidate, template, rendered_subject, rendered_body, issues)
    _validate_duplicate_history(db, candidate, email_type, issues)
    _add_approval_requirement(template, email_type, issues)
    return ValidationResult.from_issues(issues)


def _validate_candidate(candidate: Candidate, issues: list[ValidationIssue]) -> None:
    if not candidate.full_name or not candidate.full_name.strip():
        issues.append(
            _issue(
                "CANDIDATE_REQUIRED_NAME",
                IssueSeverity.ERROR,
                "Candidate must have a verified name.",
                {"candidate_id": candidate.id},
                "Add the verified candidate name.",
            )
        )

    if not candidate.email or not candidate.email.strip():
        issues.append(
            _issue(
                "CANDIDATE_REQUIRED_EMAIL",
                IssueSeverity.ERROR,
                "Candidate must have a recipient email address.",
                {"candidate_id": candidate.id},
                "Add an email address verified by HR.",
            )
        )
    elif not EMAIL_RE.fullmatch(candidate.email.strip()):
        issues.append(
            _issue(
                "CANDIDATE_EMAIL_FORMAT",
                IssueSeverity.ERROR,
                "Candidate email address has an invalid format.",
                {"candidate_id": candidate.id, "email_present": True},
                "Correct the email address after verifying it with the candidate.",
            )
        )


def _validate_status_mapping(
    candidate: Candidate,
    email_type: str,
    issues: list[ValidationIssue],
) -> None:
    if candidate.status not in STATUS_EMAIL_RULES:
        issues.append(
            _issue(
                "STATUS_UNSUPPORTED",
                IssueSeverity.BLOCKER,
                "Candidate status is not supported by an explicit email rule.",
                {"candidate_status": candidate.status},
                "Configure an approved status-to-email mapping before continuing.",
            )
        )
        return

    expected_email_type = email_type_for_status(candidate.status)
    if expected_email_type is None:
        issues.append(
            _issue(
                "STATUS_PENDING",
                IssueSeverity.BLOCKER,
                "Pending candidates cannot generate recruitment outcome emails.",
                {"candidate_status": candidate.status},
                "HR must record a verified recruitment decision first.",
            )
        )
        return

    if email_type != expected_email_type:
        issues.append(
            _issue(
                "STATUS_EMAIL_MISMATCH",
                IssueSeverity.BLOCKER,
                "Requested email type does not match the candidate status.",
                {
                    "candidate_status": candidate.status,
                    "requested_email_type": email_type,
                    "expected_email_type": expected_email_type,
                },
                "Use the mapped email type or update the policy through an approved change.",
            )
        )


def _validate_template(
    candidate: Candidate,
    template: EmailTemplate | None,
    email_type: str,
    issues: list[ValidationIssue],
) -> None:
    if template is None:
        if not email_type:
            return
        issues.append(
            _issue(
                "TEMPLATE_MISSING",
                IssueSeverity.ERROR,
                "No email template exists for the requested email type.",
                {"email_type": email_type},
                "Create and verify a template for this email type.",
            )
        )
        return

    missing_values = sorted(
        key
        for key in template.required_placeholders
        if not candidate_placeholder_value(candidate, key)
    )
    if missing_values:
        issues.append(
            _issue(
                "TEMPLATE_REQUIRED_VALUE_MISSING",
                IssueSeverity.ERROR,
                "Required candidate data is missing for the selected template.",
                {"missing_placeholders": missing_values, "template_id": template.id},
                "Add verified candidate data or use an approved template with suitable requirements.",
            )
        )

    template_placeholders = set(PLACEHOLDER_RE.findall(f"{template.subject}\n{template.body}"))
    unsupported = sorted(template_placeholders - SUPPORTED_PLACEHOLDERS)
    if unsupported:
        issues.append(
            _issue(
                "TEMPLATE_UNSUPPORTED_PLACEHOLDER",
                IssueSeverity.ERROR,
                "Template contains placeholders that the renderer does not support.",
                {"unsupported_placeholders": unsupported, "template_id": template.id},
                "Replace the placeholders or add explicit renderer support.",
            )
        )

    if email_type in SENSITIVE_EMAIL_TYPES and not template.is_sensitive:
        issues.append(
            _issue(
                "SENSITIVE_TEMPLATE_FLAG",
                IssueSeverity.ERROR,
                "Sensitive email type must use a template marked as sensitive.",
                {"email_type": email_type, "template_id": template.id},
                "Mark the verified template as sensitive before generating a draft.",
            )
        )


def _validate_rendered_draft(
    candidate: Candidate,
    template: EmailTemplate | None,
    rendered_subject: str | None,
    rendered_body: str | None,
    issues: list[ValidationIssue],
) -> None:
    if rendered_subject is None or rendered_body is None:
        return

    if not rendered_subject.strip():
        issues.append(
            _issue(
                "DRAFT_SUBJECT_REQUIRED",
                IssueSeverity.ERROR,
                "Rendered email subject cannot be empty.",
                {},
                "Add a clear subject before approval or simulation.",
            )
        )
    if not rendered_body.strip():
        issues.append(
            _issue(
                "DRAFT_BODY_REQUIRED",
                IssueSeverity.ERROR,
                "Rendered email body cannot be empty.",
                {},
                "Add the verified email content before approval or simulation.",
            )
        )

    unresolved = sorted(set(PLACEHOLDER_RE.findall(f"{rendered_subject}\n{rendered_body}")))
    if unresolved:
        issues.append(
            _issue(
                "TEMPLATE_UNRESOLVED_PLACEHOLDER",
                IssueSeverity.ERROR,
                "Rendered draft still contains unresolved placeholders.",
                {"unresolved_placeholders": unresolved},
                "Fix the template syntax or provide the verified required data.",
            )
        )

    if template is None:
        return

    rendered_content = _normalize_content(f"{rendered_subject}\n{rendered_body}")
    missing_content = [
        key
        for key in template.required_placeholders
        if (expected_value := _rendered_placeholder_value(candidate, key))
        and _normalize_content(expected_value) not in rendered_content
    ]
    required_name_keys = [
        key
        for key in template.required_placeholders
        if key in NAME_PLACEHOLDERS and candidate_placeholder_value(candidate, key)
    ]
    detected_name = _extract_greeting_name(rendered_body) if required_name_keys else None
    expected_name = (candidate.full_name or "").strip()
    has_name_mismatch = bool(
        detected_name
        and expected_name
        and not _greeting_name_matches_candidate(detected_name, expected_name)
    )
    if detected_name and has_name_mismatch:
        issues.append(
            _issue(
                "CANDIDATE_NAME_MISMATCH",
                IssueSeverity.ERROR,
                (
                    "The candidate name in the draft does not match the selected candidate. "
                    f"Expected '{expected_name}', but the greeting contains '{detected_name}'."
                ),
                {
                    "expected_candidate_name": expected_name,
                    "detected_candidate_name": detected_name,
                    "location": "body_greeting",
                    "placeholders": required_name_keys,
                },
                f"Replace '{detected_name}' with '{expected_name}', then save the draft again.",
            )
        )

    missing_without_mismatched_name = [
        key
        for key in missing_content
        if key not in NAME_PLACEHOLDERS or not has_name_mismatch
    ]
    if missing_without_mismatched_name:
        issues.append(
            _issue(
                "REQUIRED_CONTENT_MISSING",
                IssueSeverity.ERROR,
                (
                    "The draft is missing required candidate information: "
                    f"{_placeholder_labels(missing_without_mismatched_name)}."
                ),
                {"missing_placeholders": missing_without_mismatched_name},
                "Add the verified candidate information to the subject or body, then save again.",
            )
        )


def _validate_duplicate_history(
    db: Session,
    candidate: Candidate,
    email_type: str,
    issues: list[ValidationIssue],
) -> None:
    if not email_type:
        return

    already_sent = (
        db.query(EmailHistory)
        .filter(
            EmailHistory.candidate_id == candidate.id,
            EmailHistory.email_type == email_type,
        )
        .first()
    )
    if already_sent:
        issues.append(
            _issue(
                "DUPLICATE_SENT_HISTORY",
                IssueSeverity.ERROR,
                "A sent or simulated email already exists for this candidate and email type.",
                {"candidate_id": candidate.id, "email_type": email_type, "history_id": already_sent.id},
                "Review the prior history and use an explicit resend workflow if needed.",
            )
        )


def _add_approval_requirement(
    template: EmailTemplate | None,
    email_type: str,
    issues: list[ValidationIssue],
) -> None:
    requires_approval = email_type in SENSITIVE_EMAIL_TYPES or bool(template and template.is_sensitive)
    if requires_approval:
        issues.append(
            ValidationIssue(
                rule_id="REQUIRES_HR_APPROVAL",
                severity=IssueSeverity.WARNING,
                message="Sensitive draft requires explicit HR approval before simulation.",
                evidence={"email_type": email_type},
                remediation="An authorized HR reviewer must approve the final draft.",
                is_blocking=False,
            )
        )


def candidate_placeholder_value(candidate: Candidate, key: str) -> str | None:
    candidate_key = "full_name" if key == "candidate_name" else key
    value = getattr(candidate, candidate_key, None)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        value = value.strip()
    return str(value) if value else None


def _rendered_placeholder_value(candidate: Candidate, key: str) -> str | None:
    value = candidate_placeholder_value(candidate, key)
    if value is None:
        return None
    if key == "interview_time" and isinstance(candidate.interview_time, datetime):
        return candidate.interview_time.strftime("%Y-%m-%d %H:%M")
    return value


def _normalize_content(value: str) -> str:
    return " ".join(value.casefold().split())


def _extract_greeting_name(body: str) -> str | None:
    first_content_line = next((line for line in body.splitlines() if line.strip()), "")
    match = GREETING_NAME_RE.match(first_content_line)
    if match is None:
        return None
    detected_name = match.group(1).strip()
    return detected_name or None


def _greeting_name_matches_candidate(detected_name: str, expected_name: str) -> bool:
    normalized_detected = _normalize_content(detected_name)
    normalized_expected = _normalize_content(expected_name)
    return (
        normalized_detected == normalized_expected
        or normalized_detected.endswith(f" {normalized_expected}")
    )


def _placeholder_labels(placeholders: list[str]) -> str:
    labels = {
        "candidate_name": "candidate name",
        "full_name": "candidate name",
        "interview_time": "interview time",
    }
    return ", ".join(
        labels.get(placeholder, placeholder.replace("_", " "))
        for placeholder in placeholders
    )


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
