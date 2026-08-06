from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.constants.auditActions import AI_GENERATE_EMAIL, APPROVE_EMAIL, AUTO_CANCEL_EMAIL, CANCEL_EMAIL, QUEUE_AGENT_REVIEW, SEND_EMAIL
from app.constants.messages import (
    CANDIDATE_NOT_FOUND_MESSAGE,
    EMAIL_QUEUE_NOT_FOUND_MESSAGE,
    EMAIL_REQUIRES_APPROVAL_MESSAGE,
)
from app.models import Candidate, EmailHistory, EmailQueue, EmailTemplate, QueueStatus
from app.services.ai_email import get_ai_email_service
from app.services.agent_review import retain_agent_review
from app.services.audit import log_action
from app.services.draft_review_queue import create_review_outbox_event, prepare_queued_review, review_metadata
from app.services.rules import QueueAction, SENSITIVE_EMAIL_TYPES, email_type_for_status, is_queue_action_allowed
from app.services.validation import validate_email_draft


def generate_email_draft(db: Session, candidate_id: int, requested_email_type: str | None, created_by: str) -> EmailQueue:
    try:
        candidate = db.get(Candidate, candidate_id)
        if not candidate:
            raise HTTPException(status_code=404, detail=CANDIDATE_NOT_FOUND_MESSAGE)

        email_type = requested_email_type or email_type_for_status(candidate.status) or ""
        template = (
            db.query(EmailTemplate).filter(EmailTemplate.email_type == email_type).first()
            if email_type
            else None
        )
        risk = build_risk_check(db, candidate, template, email_type)
        _raise_for_invalid_risk(risk)
        if template is None:
            raise RuntimeError("Draft validation passed without a template.")

        subject, body = get_ai_email_service().generate(candidate, template, email_type)
        deterministic_risk = build_risk_check(
            db,
            candidate,
            template,
            email_type,
            rendered_subject=subject,
            rendered_body=body,
        )
        _raise_for_invalid_risk(deterministic_risk)
        queued_risk = prepare_queued_review(
            deterministic_risk,
            subject=subject,
            body=body,
        )
        requires_approval = email_type in SENSITIVE_EMAIL_TYPES or template.is_sensitive
        queue_item = EmailQueue(
            candidate_id=candidate.id,
            email_type=email_type,
            to_email=candidate.email,
            subject=subject,
            body=body,
            status=QueueStatus.PENDING_APPROVAL.value if requires_approval else QueueStatus.DRAFT.value,
            requires_hr_approval=requires_approval,
            risk_check_result=queued_risk,
            created_by=created_by,
        )
        db.add(queue_item)
        db.flush()
        create_review_outbox_event(db, queue_item)
        metadata = review_metadata(queue_item)
        log_action(
            db,
            AI_GENERATE_EMAIL,
            "email_queue",
            queue_item.id,
            created_by,
            {"candidate_id": candidate.id, "email_type": email_type},
        )
        log_action(
            db,
            QUEUE_AGENT_REVIEW,
            "email_queue",
            queue_item.id,
            created_by,
            {
                "draft_version": metadata["draft_version"],
                "content_hash": metadata["content_hash"],
            },
        )
        db.commit()
        db.refresh(queue_item)
        return queue_item
    except Exception:
        db.rollback()
        raise


def build_risk_check(
    db: Session,
    candidate: Candidate,
    template: EmailTemplate | None,
    email_type: str,
    rendered_subject: str | None = None,
    rendered_body: str | None = None,
) -> dict:
    result = validate_email_draft(
        db=db,
        candidate=candidate,
        template=template,
        email_type=email_type,
        rendered_subject=rendered_subject,
        rendered_body=rendered_body,
    )
    return result.model_dump(mode="json")


def update_email_draft(
    db: Session,
    queue_id: int,
    subject: str | None = None,
    body: str | None = None,
) -> EmailQueue:
    try:
        item = _get_queue_item(db, queue_id)
        _require_queue_action(item, QueueAction.EDIT)

        updated_subject = subject if subject is not None else item.subject
        updated_body = body if body is not None else item.body
        content_changed = updated_subject != item.subject or updated_body != item.body
        if not content_changed:
            return item

        template = _get_email_template(db, item.email_type)
        deterministic_risk = build_risk_check(
            db=db,
            candidate=item.candidate,
            template=template,
            email_type=item.email_type,
            rendered_subject=updated_subject,
            rendered_body=updated_body,
        )
        _raise_for_invalid_risk(deterministic_risk)
        queued_risk = prepare_queued_review(
            deterministic_risk,
            subject=updated_subject,
            body=updated_body,
            previous_result=item.risk_check_result,
        )

        item.subject = updated_subject
        item.body = updated_body
        item.risk_check_result = queued_risk
        item.requires_hr_approval = item.email_type in SENSITIVE_EMAIL_TYPES or bool(
            template and template.is_sensitive
        )
        item.status = (
            QueueStatus.PENDING_APPROVAL.value
            if item.requires_hr_approval
            else QueueStatus.DRAFT.value
        )
        item.approved_by = None
        create_review_outbox_event(db, item)
        metadata = review_metadata(item)
        log_action(
            db,
            QUEUE_AGENT_REVIEW,
            "email_queue",
            item.id,
            item.created_by or "demo_hr",
            {
                "draft_version": metadata["draft_version"],
                "content_hash": metadata["content_hash"],
            },
        )

        db.commit()
        db.refresh(item)
        return item
    except Exception:
        db.rollback()
        raise


def approve_email(db: Session, queue_id: int, actor: str = "demo_hr") -> EmailQueue:
    item = _get_queue_item(db, queue_id)
    _require_queue_action(item, QueueAction.APPROVE)
    _validate_queue_item(db, item)
    item.status = QueueStatus.APPROVED.value
    item.approved_by = actor
    log_action(db, APPROVE_EMAIL, "email_queue", item.id, actor)
    db.commit()
    db.refresh(item)
    return item


def cancel_email(db: Session, queue_id: int, actor: str = "demo_hr") -> EmailQueue:
    item = _get_queue_item(db, queue_id)
    _require_queue_action(item, QueueAction.CANCEL)
    item.status = QueueStatus.CANCELLED.value
    log_action(db, CANCEL_EMAIL, "email_queue", item.id, actor)
    db.commit()
    db.refresh(item)
    return item


def send_email(db: Session, queue_id: int, actor: str = "demo_hr") -> EmailQueue:
    try:
        item = _get_queue_item(db, queue_id)
        if (
            item.requires_hr_approval
            and item.status in {QueueStatus.DRAFT.value, QueueStatus.PENDING_APPROVAL.value}
        ):
            raise HTTPException(status_code=400, detail=EMAIL_REQUIRES_APPROVAL_MESSAGE)
        _require_queue_action(item, QueueAction.SIMULATE_SEND)
        _validate_queue_item(db, item)
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
        cancelled_count = _cancel_superseded_drafts(db, item, actor)
        log_action(
            db,
            SEND_EMAIL,
            "email_queue",
            item.id,
            actor,
            {"simulation": "sent", "auto_cancelled_count": cancelled_count},
        )
        db.commit()
        db.refresh(item)
        return item
    except Exception:
        db.rollback()
        raise


def _cancel_superseded_drafts(db: Session, sent_item: EmailQueue, actor: str) -> int:
    cancellable_statuses = {
        QueueStatus.DRAFT.value,
        QueueStatus.PENDING_APPROVAL.value,
        QueueStatus.APPROVED.value,
    }
    superseded_items = (
        db.query(EmailQueue)
        .filter(
            EmailQueue.id != sent_item.id,
            EmailQueue.candidate_id == sent_item.candidate_id,
            EmailQueue.email_type == sent_item.email_type,
            EmailQueue.status.in_(cancellable_statuses),
        )
        .with_for_update()
        .all()
    )
    for superseded_item in superseded_items:
        previous_status = superseded_item.status
        superseded_item.status = QueueStatus.CANCELLED.value
        log_action(
            db,
            AUTO_CANCEL_EMAIL,
            "email_queue",
            superseded_item.id,
            actor,
            {
                "reason": "superseded_by_sent_email",
                "sent_queue_id": sent_item.id,
                "previous_status": previous_status,
            },
        )
    return len(superseded_items)


def _get_queue_item(db: Session, queue_id: int) -> EmailQueue:
    item = db.get(EmailQueue, queue_id)
    if not item:
        raise HTTPException(status_code=404, detail=EMAIL_QUEUE_NOT_FOUND_MESSAGE)
    return item


def _require_queue_action(item: EmailQueue, action: QueueAction) -> None:
    if not is_queue_action_allowed(item.status, action):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot {action.value} email with status {item.status}.",
        )


def _validate_queue_item(
    db: Session,
    item: EmailQueue,
    subject: str | None = None,
    body: str | None = None,
) -> dict:
    template = _get_email_template(db, item.email_type)
    risk = build_risk_check(
        db=db,
        candidate=item.candidate,
        template=template,
        email_type=item.email_type,
        rendered_subject=subject if subject is not None else item.subject,
        rendered_body=body if body is not None else item.body,
    )
    if not risk["passed"]:
        raise HTTPException(status_code=400, detail=risk)
    merged_risk = retain_agent_review(risk, item.risk_check_result)
    item.risk_check_result = merged_risk
    return merged_risk


def _get_email_template(db: Session, email_type: str) -> EmailTemplate | None:
    return (
        db.query(EmailTemplate)
        .filter(EmailTemplate.email_type == email_type)
        .first()
    )


def _raise_for_invalid_risk(risk: dict) -> None:
    if not risk["passed"]:
        raise HTTPException(status_code=400, detail=risk)
