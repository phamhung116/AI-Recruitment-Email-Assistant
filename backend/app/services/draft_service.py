"""Transactional lifecycle service for standard email draft revisions."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.constants.templates import DECISION_CORRECTION, STAGE_DECISION_TEMPLATE_POLICY
from app.models import (
    Candidate,
    DraftRevision,
    DraftStatus,
    LogicalSendOperation,
    OperationStatus,
)
from app.schemas.validation import ValidationResult
from app.services.safety_guard import (
    CandidateSafetyFacts,
    ContradictionWorkflow,
    DraftSafetyData,
    evaluate_communication_contradiction,
    evaluate_draft_safety,
)
from app.services.template_service import (
    TemplateRenderContext,
    assemble_rendered_body,
    render_template,
)


EDITABLE_NORMAL_STATUSES = frozenset(
    {
        DraftStatus.DRAFT_PENDING_CHECK.value,
        DraftStatus.READY_TO_SEND.value,
        DraftStatus.BLOCKED_DETERMINISTIC.value,
    }
)
ACTIVE_CORRECTION_OPERATION_STATUSES = frozenset(
    {
        OperationStatus.SENDING_UNCONFIRMED.value,
        OperationStatus.DEFINITIVE_FAILURE.value,
        OperationStatus.DELIVERY_UNKNOWN.value,
    }
)


class DraftServiceError(ValueError):
    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message
        super().__init__(f"{error_code}: {message}")


def generate_draft(
    db: Session,
    *,
    application_id: str | None,
    actor: str = "demo_hr",
) -> DraftRevision:
    """Create and validate the next standard revision for one application.

    The caller owns commit/rollback. Locking the globally unique candidate row
    serializes revision-number allocation on PostgreSQL.
    """

    candidate = _load_candidate_for_update(db, application_id)
    _assert_no_frozen_draft(db, candidate.id, candidate.stage)

    template_code = STAGE_DECISION_TEMPLATE_POLICY.get(
        (candidate.stage, candidate.status), ""
    )
    rendered = render_template(
        TemplateRenderContext(
            application_id=candidate.application_id,
            candidate_name=candidate.full_name,
            recipient=candidate.email,
            stage=candidate.stage,
            decision=candidate.status,
            email_type=template_code,
        )
    )

    draft = _new_revision(
        db,
        candidate=candidate,
        template_code=rendered.template_code,
        stage=candidate.stage,
        decision=candidate.status,
        to_email=candidate.email.strip().lower(),
        subject=rendered.subject,
        decision_critical_content=rendered.decision_critical_content,
        editable_content=rendered.editable_content,
        rendered_body=rendered.rendered_body,
        actor=actor,
    )
    _validate_and_finalize(candidate, draft)
    return draft


def revise_draft(
    db: Session,
    *,
    draft_revision_id: UUID,
    editable_content: str | None = None,
    subject: str | None = None,
    actor: str = "demo_hr",
) -> DraftRevision:
    """Create a new revision for editable changes; return source for a no-op."""

    source = db.execute(
        select(DraftRevision)
        .where(DraftRevision.id == draft_revision_id)
        .with_for_update()
    ).scalar_one_or_none()
    if source is None:
        raise DraftServiceError(
            "DRAFT_REVISION_NOT_FOUND",
            "The selected draft revision no longer exists.",
        )
    _assert_normal_draft_is_editable(source)

    candidate = db.execute(
        select(Candidate)
        .where(Candidate.id == source.candidate_id)
        .with_for_update()
    ).scalar_one()
    _assert_no_frozen_draft(db, candidate.id, source.stage)
    _assert_latest_editable_revision(db, source)

    revised_editable_content = (
        source.editable_content if editable_content is None else editable_content
    )
    revised_subject = source.subject if subject is None else subject
    if (
        revised_editable_content == source.editable_content
        and revised_subject == source.subject
    ):
        return source

    rendered_body = assemble_rendered_body(
        source.decision_critical_content,
        revised_editable_content,
    )
    revised = _new_revision(
        db,
        candidate=candidate,
        template_code=source.template_code,
        stage=source.stage,
        decision=source.decision,
        to_email=source.to_email,
        subject=revised_subject,
        decision_critical_content=source.decision_critical_content,
        editable_content=revised_editable_content,
        rendered_body=rendered_body,
        actor=actor,
    )
    _validate_and_finalize(candidate, revised)
    return revised


def create_decision_correction(
    db: Session,
    *,
    application_id: str | None,
    new_decision: str | None,
    rationale: str | None,
    actor: str = "demo_hr",
) -> DraftRevision:
    """Create one controlled correction linked to the current accepted outcome."""

    candidate = _load_candidate_for_update(db, application_id)
    decision = (new_decision or "").strip().upper()
    normalized_rationale = (rationale or "").strip()
    if len(normalized_rationale) < 5:
        raise DraftServiceError(
            "CORRECTION_RATIONALE_REQUIRED",
            "A correction rationale of at least five characters is required.",
        )

    stage = candidate.stage.strip().upper()
    communicated_stage = (candidate.communicated_stage or "").strip().upper()
    communicated_decision = (candidate.communicated_decision or "").strip().upper()
    if not communicated_stage or not communicated_decision:
        raise DraftServiceError(
            "COMMUNICATED_OUTCOME_REQUIRED",
            "A provider-accepted communicated outcome is required before correction.",
        )
    if communicated_stage != stage:
        raise DraftServiceError(
            "CORRECTION_STAGE_MISMATCH",
            "The correction stage must match the current communicated outcome stage.",
        )
    if decision == communicated_decision:
        raise DraftServiceError(
            "CORRECTION_NOT_REQUIRED",
            "The proposed decision matches the outcome already communicated.",
        )
    if (stage, decision) not in STAGE_DECISION_TEMPLATE_POLICY:
        raise DraftServiceError(
            "STATUS_UNSUPPORTED",
            "The proposed correction decision is not supported for this hiring stage.",
        )

    _assert_no_frozen_draft(db, candidate.id, stage)
    _assert_no_active_correction(db, candidate.id, stage)
    prior_operation = _load_prior_accepted_operation(
        db,
        candidate_id=candidate.id,
        stage=stage,
        decision=communicated_decision,
    )

    rendered = render_template(
        TemplateRenderContext(
            application_id=candidate.application_id,
            candidate_name=candidate.full_name,
            recipient=candidate.email,
            stage=stage,
            decision=decision,
            email_type=DECISION_CORRECTION,
            is_correction=True,
        )
    )
    draft = DraftRevision(
        candidate_id=candidate.id,
        revision_number=_next_revision_number(db, candidate.id),
        template_code=rendered.template_code,
        stage=stage,
        decision=decision,
        to_email=candidate.email.strip().lower(),
        subject=rendered.subject,
        decision_critical_content=rendered.decision_critical_content,
        editable_content=rendered.editable_content,
        rendered_body=rendered.rendered_body,
        status=DraftStatus.CORRECTION_DRAFT.value,
        is_correction=True,
        correction_rationale=normalized_rationale,
        prior_operation_id=prior_operation.id,
        risk_check_result={},
        created_by=actor,
    )
    result = _evaluate_revision(
        candidate,
        draft,
        workflow=ContradictionWorkflow.CORRECTION,
        candidate_status=decision,
    )
    draft.risk_check_result = result.model_dump(mode="json")
    candidate.status = decision
    candidate.status_updated_at = datetime.now(timezone.utc)
    candidate.status_updated_by = actor
    db.add(draft)
    db.flush()
    return draft


def discard_decision_correction(
    db: Session,
    *,
    draft_revision_id: UUID,
) -> DraftRevision:
    """Discard an unsent correction without changing communicated outcome fields."""

    draft = db.execute(
        select(DraftRevision)
        .where(DraftRevision.id == draft_revision_id)
        .with_for_update()
    ).scalar_one_or_none()
    if draft is None:
        raise DraftServiceError(
            "DRAFT_REVISION_NOT_FOUND",
            "The selected correction draft no longer exists.",
        )
    if not draft.is_correction:
        raise DraftServiceError(
            "CORRECTION_DRAFT_REQUIRED",
            "Only a decision correction draft can be discarded by this workflow.",
        )
    if draft.status != DraftStatus.CORRECTION_DRAFT.value:
        raise DraftServiceError(
            "CORRECTION_NOT_DISCARDABLE",
            "A correction can only be discarded before transmission begins.",
        )
    operation_exists = db.execute(
        select(LogicalSendOperation.id)
        .where(LogicalSendOperation.draft_revision_id == draft.id)
        .limit(1)
    ).scalar_one_or_none()
    if operation_exists is not None:
        raise DraftServiceError(
            "CORRECTION_NOT_DISCARDABLE",
            "A correction with a send operation can no longer be discarded.",
        )
    draft.status = DraftStatus.DISCARDED.value
    draft.discarded_at = datetime.now(timezone.utc)
    return draft


def _load_candidate_for_update(
    db: Session,
    application_id: str | None,
) -> Candidate:
    normalized_application_id = (application_id or "").strip()
    if not normalized_application_id:
        raise DraftServiceError(
            "APPLICATION_ID_REQUIRED",
            "Application ID is required to create a draft.",
        )
    candidate = db.execute(
        select(Candidate)
        .where(Candidate.application_id == normalized_application_id)
        .with_for_update()
    ).scalar_one_or_none()
    if candidate is None:
        raise DraftServiceError(
            "APPLICATION_NOT_FOUND",
            "The selected application no longer exists.",
        )
    return candidate


def _assert_no_frozen_draft(db: Session, candidate_id: int, stage: str) -> None:
    frozen_id = db.execute(
        select(DraftRevision.id)
        .where(
            DraftRevision.candidate_id == candidate_id,
            DraftRevision.stage == stage,
            DraftRevision.status == DraftStatus.FROZEN_IN_FLIGHT.value,
        )
        .limit(1)
    ).scalar_one_or_none()
    if frozen_id is not None:
        raise DraftServiceError(
            "DRAFT_FROZEN_IN_FLIGHT",
            "A draft for this application stage is currently being sent.",
        )


def _assert_normal_draft_is_editable(draft: DraftRevision) -> None:
    if draft.is_correction:
        raise DraftServiceError(
            "CORRECTION_WORKFLOW_REQUIRED",
            "Decision correction drafts must be edited through the correction workflow.",
        )
    if draft.status == DraftStatus.FROZEN_IN_FLIGHT.value:
        raise DraftServiceError(
            "DRAFT_FROZEN_IN_FLIGHT",
            "The draft is frozen while its send operation is in progress.",
        )
    if draft.status == DraftStatus.SUPERSEDED.value:
        raise DraftServiceError(
            "DRAFT_REVISION_STALE",
            "A superseded draft revision cannot be edited.",
        )
    if draft.status not in EDITABLE_NORMAL_STATUSES:
        raise DraftServiceError(
            "DRAFT_NOT_EDITABLE",
            f"A draft in {draft.status} status cannot be edited.",
        )


def _assert_latest_editable_revision(db: Session, source: DraftRevision) -> None:
    latest_id = db.execute(
        select(DraftRevision.id)
        .where(
            DraftRevision.candidate_id == source.candidate_id,
            DraftRevision.stage == source.stage,
            DraftRevision.is_correction.is_(False),
            DraftRevision.status.in_(EDITABLE_NORMAL_STATUSES),
        )
        .order_by(DraftRevision.revision_number.desc())
        .limit(1)
    ).scalar_one_or_none()
    if latest_id != source.id:
        raise DraftServiceError(
            "DRAFT_REVISION_STALE",
            "A newer active draft revision already exists for this application stage.",
        )


def _assert_no_active_correction(db: Session, candidate_id: int, stage: str) -> None:
    active_id = db.execute(
        select(DraftRevision.id)
        .outerjoin(
            LogicalSendOperation,
            LogicalSendOperation.draft_revision_id == DraftRevision.id,
        )
        .where(
            DraftRevision.candidate_id == candidate_id,
            DraftRevision.stage == stage,
            DraftRevision.is_correction.is_(True),
            or_(
                DraftRevision.status.in_(
                    {
                        DraftStatus.CORRECTION_DRAFT.value,
                        DraftStatus.FROZEN_IN_FLIGHT.value,
                    }
                ),
                LogicalSendOperation.operation_status.in_(
                    ACTIVE_CORRECTION_OPERATION_STATUSES
                ),
            ),
        )
        .limit(1)
    ).scalar_one_or_none()
    if active_id is not None:
        raise DraftServiceError(
            "ACTIVE_CORRECTION_EXISTS",
            "An active correction already exists for this application stage.",
        )


def _load_prior_accepted_operation(
    db: Session,
    *,
    candidate_id: int,
    stage: str,
    decision: str,
) -> LogicalSendOperation:
    operation = db.execute(
        select(LogicalSendOperation)
        .join(
            DraftRevision,
            LogicalSendOperation.draft_revision_id == DraftRevision.id,
        )
        .where(
            DraftRevision.candidate_id == candidate_id,
            DraftRevision.stage == stage,
            DraftRevision.decision == decision,
            LogicalSendOperation.operation_status
            == OperationStatus.PROVIDER_ACCEPTED.value,
        )
        .order_by(
            LogicalSendOperation.updated_at.desc(),
            LogicalSendOperation.created_at.desc(),
        )
        .limit(1)
    ).scalar_one_or_none()
    if operation is None:
        raise DraftServiceError(
            "PRIOR_ACCEPTED_OPERATION_NOT_FOUND",
            "No provider-accepted email was found for the communicated outcome.",
        )
    return operation


def _next_revision_number(db: Session, candidate_id: int) -> int:
    return (
        db.execute(
            select(func.coalesce(func.max(DraftRevision.revision_number), 0)).where(
                DraftRevision.candidate_id == candidate_id
            )
        ).scalar_one()
        + 1
    )


def _new_revision(
    db: Session,
    *,
    candidate: Candidate,
    template_code: str,
    stage: str,
    decision: str,
    to_email: str,
    subject: str,
    decision_critical_content: str,
    editable_content: str,
    rendered_body: str,
    actor: str,
) -> DraftRevision:
    next_revision_number = _next_revision_number(db, candidate.id)
    now = datetime.now(timezone.utc)
    older_drafts = db.execute(
        select(DraftRevision)
        .where(
            DraftRevision.candidate_id == candidate.id,
            DraftRevision.stage == stage,
            DraftRevision.is_correction.is_(False),
            DraftRevision.status.in_(EDITABLE_NORMAL_STATUSES),
        )
        .with_for_update()
    ).scalars()
    for older_draft in older_drafts:
        older_draft.status = DraftStatus.SUPERSEDED.value
        older_draft.superseded_at = now

    draft = DraftRevision(
        candidate_id=candidate.id,
        revision_number=next_revision_number,
        template_code=template_code,
        stage=stage,
        decision=decision,
        to_email=to_email,
        subject=subject,
        decision_critical_content=decision_critical_content,
        editable_content=editable_content,
        rendered_body=rendered_body,
        status=DraftStatus.DRAFT_PENDING_CHECK.value,
        is_correction=False,
        risk_check_result={},
        created_by=actor,
    )
    db.add(draft)
    db.flush()
    return draft


def _validate_and_finalize(candidate: Candidate, draft: DraftRevision) -> None:
    result = _evaluate_revision(candidate, draft)
    draft.status = (
        DraftStatus.READY_TO_SEND.value
        if result.passed
        else DraftStatus.BLOCKED_DETERMINISTIC.value
    )
    draft.risk_check_result = result.model_dump(mode="json")


def _evaluate_revision(
    candidate: Candidate,
    draft: DraftRevision,
    *,
    workflow: ContradictionWorkflow = ContradictionWorkflow.NORMAL,
    candidate_status: str | None = None,
) -> ValidationResult:
    candidate_facts = CandidateSafetyFacts(
        application_id=candidate.application_id,
        full_name=candidate.full_name,
        email=candidate.email,
        stage=candidate.stage,
        status=candidate.status if candidate_status is None else candidate_status,
    )
    draft_data = DraftSafetyData(
        application_id=candidate.application_id,
        stage=draft.stage,
        decision=draft.decision,
        recipient=draft.to_email,
        email_type=draft.template_code,
        subject=draft.subject,
        decision_critical_content=draft.decision_critical_content,
        editable_content=draft.editable_content,
        rendered_body=draft.rendered_body,
        is_correction=draft.is_correction,
    )
    local_result = evaluate_draft_safety(candidate_facts, draft_data)
    contradiction_result = evaluate_communication_contradiction(
        candidate,
        proposed_stage=draft.stage,
        proposed_decision=draft.decision,
        workflow=workflow,
    )
    result = ValidationResult.from_issues(
        [*local_result.issues, *contradiction_result.issues]
    )
    return result
