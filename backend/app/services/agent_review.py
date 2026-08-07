from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.agents import RecruitmentEmailAgent
from app.constants.auditActions import AGENT_REVIEW_EMAIL
from app.constants.messages import EMAIL_QUEUE_NOT_FOUND_MESSAGE
from app.models import Candidate, EmailQueue, EmailTemplate, QueueStatus
from app.schemas.agent import (
    AgentCandidateFacts,
    AgentDraftInput,
    AgentReviewRequest,
    AgentReviewResult,
    AgentReviewStatus,
    AgentTemplateInput,
)
from app.schemas.validation import ValidationResult
from app.services.audit import log_action
from app.services.rules import QueueAction, SENSITIVE_EMAIL_TYPES, is_queue_action_allowed
from app.services.validation import validate_email_draft


COMPANY_POLICIES = [
    "HR remains the final decision-maker for every recruitment outcome.",
    "Sensitive or uncertain drafts require explicit HR review.",
    "Email delivery is simulated in this MVP; never claim real delivery.",
]


def review_email_content(
    *,
    candidate: Candidate,
    template: EmailTemplate,
    email_type: str,
    subject: str,
    body: str,
    deterministic_validation: ValidationResult,
    agent: RecruitmentEmailAgent | None = None,
) -> AgentReviewResult:
    request = AgentReviewRequest(
        candidate=AgentCandidateFacts(
            full_name=candidate.full_name,
            position=candidate.position,
            status=candidate.status,
            interview_time=_format_datetime(candidate.interview_time),
            interviewer=candidate.interviewer,
        ),
        email_type=email_type,
        template=AgentTemplateInput(
            name=template.name,
            email_type=template.email_type,
            subject=template.subject,
            body=template.body,
            is_sensitive=template.is_sensitive,
        ),
        draft=AgentDraftInput(subject=subject, body=body),
        deterministic_validation=deterministic_validation,
        company_policy=COMPANY_POLICIES,
    )
    return (agent or RecruitmentEmailAgent()).review(request)


def validate_and_review_email_content(
    *,
    db: Session,
    candidate: Candidate,
    template: EmailTemplate | None,
    email_type: str,
    subject: str,
    body: str,
    agent: RecruitmentEmailAgent | None = None,
) -> tuple[ValidationResult, AgentReviewResult]:
    deterministic = validate_email_draft(
        db=db,
        candidate=candidate,
        template=template,
        email_type=email_type,
        rendered_subject=subject,
        rendered_body=body,
    )
    if not deterministic.passed:
        raise HTTPException(
            status_code=400,
            detail=deterministic.model_dump(mode="json"),
        )
    if template is None:
        raise RuntimeError("Draft validation passed without a template.")

    review = review_email_content(
        candidate=candidate,
        template=template,
        email_type=email_type,
        subject=subject,
        body=body,
        deterministic_validation=deterministic,
        agent=agent,
    )
    return deterministic, review


def review_queue_draft(
    db: Session,
    queue_id: int,
    actor: str = "demo_hr",
    agent: RecruitmentEmailAgent | None = None,
) -> AgentReviewResult:
    item = db.get(EmailQueue, queue_id)
    if item is None:
        raise HTTPException(status_code=404, detail=EMAIL_QUEUE_NOT_FOUND_MESSAGE)
    if not is_queue_action_allowed(item.status, QueueAction.REVIEW):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot review email with status {item.status}.",
        )

    template = (
        db.query(EmailTemplate)
        .filter(EmailTemplate.email_type == item.email_type)
        .first()
    )
    deterministic, review = validate_and_review_email_content(
        db=db,
        candidate=item.candidate,
        template=template,
        email_type=item.email_type,
        subject=item.subject,
        body=item.body,
        agent=agent,
    )
    item.risk_check_result = merge_review_result(
        deterministic.model_dump(mode="json"),
        review,
    )
    _apply_review_requirement(item, template, review)
    log_action(
        db,
        AGENT_REVIEW_EMAIL,
        "email_queue",
        item.id,
        actor,
        agent_review_audit_metadata(review),
    )
    db.commit()
    db.refresh(item)
    return review


def merge_review_result(
    deterministic_result: dict,
    review: AgentReviewResult,
) -> dict:
    merged = dict(deterministic_result)
    merged["agent_review"] = review.model_dump(mode="json")
    merged["requires_human_review"] = review.requires_human_review
    return merged


def retain_agent_review(
    deterministic_result: dict,
    previous_result: dict | None,
) -> dict:
    if not previous_result:
        return deterministic_result

    merged = dict(deterministic_result)
    for key in ("agent_review", "draft_version", "content_hash", "async_review"):
        if key in previous_result:
            merged[key] = previous_result[key]

    if "requires_human_review" in previous_result:
        merged["requires_human_review"] = bool(previous_result["requires_human_review"])

    return merged


def agent_review_audit_metadata(review: AgentReviewResult) -> dict:
    return {
        "status": review.status.value,
        "provider": review.model_metadata.provider,
        "model": review.model_metadata.model,
        "prompt_version": review.model_metadata.prompt_version,
        "skill_version": review.model_metadata.skill_version,
        "attempts": review.model_metadata.attempts,
        "loop_steps": review.model_metadata.loop_steps,
        "tool_calls": review.model_metadata.tool_calls,
        "issue_count": len(review.issues),
        "requires_human_review": review.requires_human_review,
    }


def _apply_review_requirement(
    item: EmailQueue,
    template: EmailTemplate,
    review: AgentReviewResult,
) -> None:
    requires_approval = (
        item.email_type in SENSITIVE_EMAIL_TYPES
        or template.is_sensitive
        or review.requires_human_review
    )
    item.requires_hr_approval = requires_approval

    must_reset_approval = review.status == AgentReviewStatus.UNAVAILABLE or bool(
        review.issues
    ) or review.uncertainty.has_uncertainty
    if item.status == QueueStatus.APPROVED.value and must_reset_approval:
        item.status = QueueStatus.PENDING_APPROVAL.value
        item.approved_by = None
    elif item.status in {
        QueueStatus.DRAFT.value,
        QueueStatus.PENDING_APPROVAL.value,
    }:
        item.status = (
            QueueStatus.PENDING_APPROVAL.value
            if requires_approval
            else QueueStatus.DRAFT.value
        )


def _format_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
