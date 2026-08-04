import re
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.constants.auditActions import AI_GENERATE_EMAIL, APPROVE_EMAIL, CANCEL_EMAIL, SEND_EMAIL
from app.constants.messages import (
    CANDIDATE_NOT_FOUND_MESSAGE,
    EMAIL_QUEUE_NOT_FOUND_MESSAGE,
    EMAIL_REQUIRES_APPROVAL_MESSAGE,
    PENDING_STATUS_MESSAGE,
)
from app.models import Candidate, EmailHistory, EmailQueue, EmailTemplate, QueueStatus
from app.services.ai_email import get_ai_email_service
from app.services.audit import log_action
from app.services.rules import SEND_STATUS_TRANSITIONS, SENSITIVE_EMAIL_TYPES, email_type_for_status


PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


def generate_email_draft(db: Session, candidate_id: int, requested_email_type: str | None, created_by: str) -> EmailQueue:
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail=CANDIDATE_NOT_FOUND_MESSAGE)

    expected_email_type = email_type_for_status(candidate.status)
    if expected_email_type is None:
        raise HTTPException(status_code=400, detail=PENDING_STATUS_MESSAGE)

    email_type = requested_email_type or expected_email_type
    if email_type != expected_email_type:
        raise HTTPException(status_code=400, detail=f"Email type {email_type} does not match status {candidate.status}. Expected {expected_email_type}.")

    template = db.query(EmailTemplate).filter(EmailTemplate.email_type == email_type).first()
    risk = build_risk_check(db, candidate, template, email_type)
    if not risk["passed"]:
        raise HTTPException(status_code=400, detail=risk)

    subject, body = get_ai_email_service().generate(candidate, template, email_type)
    requires_approval = email_type in SENSITIVE_EMAIL_TYPES or template.is_sensitive
    queue_status = QueueStatus.PENDING_APPROVAL.value if requires_approval else QueueStatus.DRAFT.value
    queue_item = EmailQueue(
        candidate_id=candidate.id,
        email_type=email_type,
        to_email=candidate.email,
        subject=subject,
        body=body,
        status=queue_status,
        requires_hr_approval=requires_approval,
        risk_check_result=risk,
        created_by=created_by,
    )
    db.add(queue_item)
    db.flush()
    log_action(db, AI_GENERATE_EMAIL, "email_queue", queue_item.id, created_by, {"candidate_id": candidate.id, "email_type": email_type})
    db.commit()
    db.refresh(queue_item)
    return queue_item


def build_risk_check(db: Session, candidate: Candidate, template: EmailTemplate | None, email_type: str) -> dict:
    errors: list[str] = []
    if not candidate.email:
        errors.append("Candidate must have email.")
    if email_type_for_status(candidate.status) is None:
        errors.append(PENDING_STATUS_MESSAGE)
    elif email_type_for_status(candidate.status) != email_type:
        errors.append("Email type does not match candidate status.")
    if not template:
        errors.append("Template must exist.")
    else:
        missing = [key for key in template.required_placeholders if not _candidate_placeholder_value(candidate, key)]
        if missing:
            errors.append(f"Template missing required placeholder values: {', '.join(missing)}.")
        unresolved = sorted(set(PLACEHOLDER_RE.findall(template.subject + "\n" + template.body)) - _supported_placeholders())
        if unresolved:
            errors.append(f"Template contains unsupported placeholders: {', '.join(unresolved)}.")
    already_sent = (
        db.query(EmailHistory)
        .filter(EmailHistory.candidate_id == candidate.id, EmailHistory.email_type == email_type)
        .first()
    )
    if already_sent:
        errors.append("A SENT email history already exists for this candidate and email type.")
    if email_type in SENSITIVE_EMAIL_TYPES and template and not template.is_sensitive:
        errors.append("Sensitive email template must be marked is_sensitive=true.")

    return {"passed": not errors, "errors": errors, "checked_at": datetime.now(timezone.utc).isoformat()}


def approve_email(db: Session, queue_id: int, actor: str = "demo_hr") -> EmailQueue:
    item = _get_queue_item(db, queue_id)
    if item.status in {QueueStatus.SENT.value, QueueStatus.CANCELLED.value}:
        raise HTTPException(status_code=400, detail="Cannot approve sent or cancelled email.")
    item.status = QueueStatus.APPROVED.value
    item.approved_by = actor
    log_action(db, APPROVE_EMAIL, "email_queue", item.id, actor)
    db.commit()
    db.refresh(item)
    return item


def cancel_email(db: Session, queue_id: int, actor: str = "demo_hr") -> EmailQueue:
    item = _get_queue_item(db, queue_id)
    if item.status == QueueStatus.SENT.value:
        raise HTTPException(status_code=400, detail="Cannot cancel sent email.")
    item.status = QueueStatus.CANCELLED.value
    log_action(db, CANCEL_EMAIL, "email_queue", item.id, actor)
    db.commit()
    db.refresh(item)
    return item


def send_email(db: Session, queue_id: int, actor: str = "demo_hr") -> EmailQueue:
    item = _get_queue_item(db, queue_id)
    if item.requires_hr_approval and item.status != QueueStatus.APPROVED.value:
        raise HTTPException(status_code=400, detail=EMAIL_REQUIRES_APPROVAL_MESSAGE)
    if item.status in {QueueStatus.SENT.value, QueueStatus.CANCELLED.value, QueueStatus.FAILED.value}:
        raise HTTPException(status_code=400, detail=f"Cannot send email with status {item.status}.")
    if "mock_fail" in item.to_email:
        item.status = QueueStatus.FAILED.value
        log_action(db, SEND_EMAIL, "email_queue", item.id, actor, {"simulation": "failed"})
        db.commit()
        db.refresh(item)
        return item

    now = datetime.now(timezone.utc)
    item.status = QueueStatus.SENT.value
    item.sent_at = now
    db.add(
        EmailHistory(
            candidate_id=item.candidate_id,
            email_type=item.email_type,
            to_email=item.to_email,
            subject=item.subject,
            body=item.body,
            sent_by=actor,
            sent_at=now,
        )
    )
    transition = SEND_STATUS_TRANSITIONS.get(item.email_type)
    if transition:
        item.candidate.stage = transition["stage"]
        item.candidate.status = transition["status"]
    log_action(db, SEND_EMAIL, "email_queue", item.id, actor, {"simulation": "sent"})
    db.commit()
    db.refresh(item)
    return item


def _get_queue_item(db: Session, queue_id: int) -> EmailQueue:
    item = db.get(EmailQueue, queue_id)
    if not item:
        raise HTTPException(status_code=404, detail=EMAIL_QUEUE_NOT_FOUND_MESSAGE)
    return item


def _supported_placeholders() -> set[str]:
    return {"full_name", "candidate_name", "email", "phone", "position", "stage", "status", "interview_time", "interviewer", "note", "email_type"}


def _candidate_placeholder_value(candidate: Candidate, key: str) -> str | None:
    if key == "candidate_name":
        key = "full_name"
    value = getattr(candidate, key, None)
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value) if value else None
