"""Logical send operation lifecycle and concurrency boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.resend_adapter import ResendEmail, ResendEmailAdapter, ResendSendResult, digest_payload
from app.db.database import session_scope
from app.models import (
    ActionOutcome,
    AttemptStatus,
    Candidate,
    DraftRevision,
    DraftStatus,
    FailureCategory,
    LogicalSendOperation,
    OperationStatus,
    ProviderAttempt,
    ResolutionMode,
)
from app.services.audit_service import AuditEvent, append_audit_event


SENDABLE_DRAFT_STATUSES = frozenset(
    {
        DraftStatus.READY_TO_SEND.value,
        DraftStatus.CORRECTION_DRAFT.value,
    }
)
RESEND_IDEMPOTENCY_WINDOW_HOURS = 24


class DeliveryUnknownResolution(str, Enum):
    PROVIDER_ACCEPTED = "PROVIDER_ACCEPTED"
    PROVIDER_NOT_RECEIVED = "PROVIDER_NOT_RECEIVED"


class SendOrchestratorError(ValueError):
    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message
        super().__init__(f"{error_code}: {message}")


@dataclass(frozen=True)
class SendExecutionResult:
    operation_id: UUID
    operation_status: str
    attempt_id: UUID | None
    provider_message_id: str | None
    provider_call_performed: bool


@dataclass(frozen=True)
class _PreparedAttempt:
    operation_id: UUID
    attempt_id: UUID | None
    email: ResendEmail | None
    provider_call_required: bool


def prepare_logical_send_operation(
    db: Session,
    *,
    draft_revision_id: UUID,
    actor: str = "demo_hr",
) -> LogicalSendOperation:
    """Create or return the one logical operation bound to a draft revision.

    The caller owns commit/rollback. PostgreSQL serializes competing requests
    on the draft row; the database unique constraint remains the final guard
    against more than one operation per revision.
    """

    draft = db.execute(
        select(DraftRevision)
        .where(DraftRevision.id == draft_revision_id)
        .with_for_update()
    ).scalar_one_or_none()
    if draft is None:
        raise SendOrchestratorError(
            "DRAFT_REVISION_NOT_FOUND",
            "The selected draft revision no longer exists.",
        )

    existing = db.execute(
        select(LogicalSendOperation)
        .where(LogicalSendOperation.draft_revision_id == draft.id)
        .with_for_update()
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    _assert_draft_can_start_send(draft)

    operation = LogicalSendOperation(
        draft_revision_id=draft.id,
        operation_status=OperationStatus.SENDING_UNCONFIRMED.value,
        provider_name="RESEND",
        created_by=actor,
    )
    draft.status = DraftStatus.FROZEN_IN_FLIGHT.value
    db.add(operation)
    db.flush()
    return operation


def execute_initial_send(
    session_factory: Callable[[], Session],
    *,
    adapter: ResendEmailAdapter,
    draft_revision_id: UUID,
    actor: str = "demo_hr",
) -> SendExecutionResult:
    """Execute the approved Phase A -> B -> C initial send workflow."""

    with session_scope(session_factory) as phase_a_db:
        prepared = _prepare_initial_attempt(
            phase_a_db,
            adapter=adapter,
            draft_revision_id=draft_revision_id,
            actor=actor,
        )

    if not prepared.provider_call_required:
        return _operation_result(
            session_factory,
            operation_id=prepared.operation_id,
            provider_call_performed=False,
        )
    if prepared.attempt_id is None or prepared.email is None:
        raise RuntimeError("Prepared provider attempt is incomplete.")

    provider_result = adapter.send_email(
        operation_id=prepared.operation_id,
        email=prepared.email,
    )

    with session_scope(session_factory) as phase_c_db:
        _finalize_initial_attempt(
            phase_c_db,
            operation_id=prepared.operation_id,
            attempt_id=prepared.attempt_id,
            provider_result=provider_result,
            actor=actor,
        )

    return _operation_result(
        session_factory,
        operation_id=prepared.operation_id,
        provider_call_performed=True,
    )


def retry_definitive_failure(
    session_factory: Callable[[], Session],
    *,
    adapter: ResendEmailAdapter,
    operation_id: UUID,
    actor: str = "demo_hr",
) -> SendExecutionResult:
    """Retry an explicitly retryable failure on the same operation identity."""

    with session_scope(session_factory) as phase_a_db:
        prepared = _prepare_retry_attempt(
            phase_a_db,
            adapter=adapter,
            operation_id=operation_id,
            actor=actor,
        )

    if not prepared.provider_call_required:
        return _operation_result(
            session_factory,
            operation_id=prepared.operation_id,
            provider_call_performed=False,
        )
    if prepared.attempt_id is None or prepared.email is None:
        raise RuntimeError("Prepared retry attempt is incomplete.")

    provider_result = adapter.send_email(
        operation_id=prepared.operation_id,
        email=prepared.email,
    )
    with session_scope(session_factory) as phase_c_db:
        _finalize_initial_attempt(
            phase_c_db,
            operation_id=prepared.operation_id,
            attempt_id=prepared.attempt_id,
            provider_result=provider_result,
            actor=actor,
        )
    return _operation_result(
        session_factory,
        operation_id=prepared.operation_id,
        provider_call_performed=True,
    )


def reconcile_delivery_unknown_via_provider(
    session_factory: Callable[[], Session],
    *,
    adapter: ResendEmailAdapter,
    operation_id: UUID,
    current_time: datetime | None = None,
    actor: str = "demo_hr",
) -> SendExecutionResult:
    """Replay the exact request inside Resend's 24-hour idempotency window."""

    with session_scope(session_factory) as phase_a_db:
        prepared = _prepare_unknown_replay(
            phase_a_db,
            adapter=adapter,
            operation_id=operation_id,
            current_time=current_time or datetime.now(timezone.utc),
            actor=actor,
        )
    if not prepared.provider_call_required:
        return _operation_result(
            session_factory,
            operation_id=prepared.operation_id,
            provider_call_performed=False,
        )
    if prepared.attempt_id is None or prepared.email is None:
        raise RuntimeError("Prepared reconciliation attempt is incomplete.")

    provider_result = adapter.send_email(
        operation_id=prepared.operation_id,
        email=prepared.email,
    )
    with session_scope(session_factory) as phase_c_db:
        _finalize_initial_attempt(
            phase_c_db,
            operation_id=prepared.operation_id,
            attempt_id=prepared.attempt_id,
            provider_result=provider_result,
            actor=actor,
        )
    return _operation_result(
        session_factory,
        operation_id=prepared.operation_id,
        provider_call_performed=True,
    )


def resolve_delivery_unknown(
    db: Session,
    *,
    operation_id: UUID,
    resolution: DeliveryUnknownResolution,
    rationale: str | None,
    resolved_by: str | None,
    warning_acknowledged: bool,
) -> LogicalSendOperation:
    """Apply an explicit HR resolution after external status verification."""

    normalized_rationale = (rationale or "").strip()
    normalized_actor = (resolved_by or "").strip()
    if not warning_acknowledged:
        raise SendOrchestratorError(
            "RESOLUTION_WARNING_ACKNOWLEDGEMENT_REQUIRED",
            "The delivery uncertainty warning must be acknowledged.",
        )
    if len(normalized_rationale) < 5:
        raise SendOrchestratorError(
            "RESOLUTION_RATIONALE_REQUIRED",
            "A resolution rationale of at least five characters is required.",
        )
    if not normalized_actor:
        raise SendOrchestratorError(
            "RESOLVED_BY_REQUIRED",
            "The recruiter resolving delivery status is required.",
        )

    operation = db.execute(
        select(LogicalSendOperation)
        .where(LogicalSendOperation.id == operation_id)
        .with_for_update()
    ).scalar_one_or_none()
    if operation is None:
        raise SendOrchestratorError(
            "SEND_OPERATION_NOT_FOUND",
            "The logical send operation no longer exists.",
        )
    if operation.operation_status != OperationStatus.DELIVERY_UNKNOWN.value:
        raise SendOrchestratorError(
            "DELIVERY_UNKNOWN_REQUIRED",
            "Only a delivery-unknown operation can be manually resolved.",
        )

    now = datetime.now(timezone.utc)
    operation.resolution_mode = ResolutionMode.HR_MANUAL_OVERRIDE.value
    operation.resolution_rationale = normalized_rationale
    operation.resolved_by = normalized_actor
    operation.resolved_at = now
    draft = operation.draft_revision

    if resolution == DeliveryUnknownResolution.PROVIDER_ACCEPTED:
        operation.operation_status = OperationStatus.PROVIDER_ACCEPTED.value
        operation.final_outcome = OperationStatus.PROVIDER_ACCEPTED.value
        operation.failure_category = None
        candidate = db.execute(
            select(Candidate)
            .where(Candidate.id == draft.candidate_id)
            .with_for_update()
        ).scalar_one()
        candidate.communicated_decision = draft.decision
        candidate.communicated_stage = draft.stage
        candidate.communicated_at = now
    elif resolution == DeliveryUnknownResolution.PROVIDER_NOT_RECEIVED:
        operation.operation_status = OperationStatus.DEFINITIVE_FAILURE.value
        operation.final_outcome = OperationStatus.DEFINITIVE_FAILURE.value
        operation.failure_category = FailureCategory.TRANSIENT_RETRYABLE.value
    else:
        raise SendOrchestratorError(
            "DELIVERY_RESOLUTION_UNSUPPORTED",
            "The selected delivery resolution is not supported.",
        )
    append_audit_event(
        db,
        event=AuditEvent.DELIVERY_UNKNOWN_RESOLVED,
        entity_type="LOGICAL_SEND_OPERATION",
        entity_id=operation.id,
        application_id=draft.candidate.application_id,
        actor=normalized_actor,
        payload={
            "resolution": resolution.value,
            "resolution_mode": operation.resolution_mode,
            "operation_status": operation.operation_status,
            "warning_acknowledged": True,
        },
    )
    return operation


def _prepare_initial_attempt(
    db: Session,
    *,
    adapter: ResendEmailAdapter,
    draft_revision_id: UUID,
    actor: str,
) -> _PreparedAttempt:
    operation = prepare_logical_send_operation(
        db,
        draft_revision_id=draft_revision_id,
        actor=actor,
    )
    existing_attempt = db.execute(
        select(ProviderAttempt)
        .where(ProviderAttempt.operation_id == operation.id)
        .order_by(ProviderAttempt.attempt_number.desc())
        .limit(1)
        .with_for_update()
    ).scalar_one_or_none()
    if existing_attempt is not None:
        return _PreparedAttempt(
            operation_id=operation.id,
            attempt_id=existing_attempt.id,
            email=None,
            provider_call_required=False,
        )
    if operation.operation_status != OperationStatus.SENDING_UNCONFIRMED.value:
        raise SendOrchestratorError(
            "SEND_OPERATION_NOT_RETRYABLE",
            f"A send operation in {operation.operation_status} cannot create its initial attempt.",
        )

    draft = operation.draft_revision
    email = ResendEmail(
        to_email=draft.to_email,
        subject=draft.subject,
        body=draft.rendered_body,
    )
    attempt = ProviderAttempt(
        operation_id=operation.id,
        attempt_number=1,
        request_payload_digest=digest_payload(adapter.build_payload(email)),
        attempt_status=AttemptStatus.PREPARED.value,
    )
    db.add(attempt)
    db.flush()
    _audit_send_prepared(db, operation=operation, attempt=attempt, actor=actor)
    return _PreparedAttempt(
        operation_id=operation.id,
        attempt_id=attempt.id,
        email=email,
        provider_call_required=True,
    )


def _prepare_retry_attempt(
    db: Session,
    *,
    adapter: ResendEmailAdapter,
    operation_id: UUID,
    actor: str = "demo_hr",
) -> _PreparedAttempt:
    operation = db.execute(
        select(LogicalSendOperation)
        .where(LogicalSendOperation.id == operation_id)
        .with_for_update()
    ).scalar_one_or_none()
    if operation is None:
        raise SendOrchestratorError(
            "SEND_OPERATION_NOT_FOUND",
            "The logical send operation no longer exists.",
        )
    latest_attempt = db.execute(
        select(ProviderAttempt)
        .where(ProviderAttempt.operation_id == operation.id)
        .order_by(ProviderAttempt.attempt_number.desc())
        .limit(1)
        .with_for_update()
    ).scalar_one_or_none()
    if latest_attempt is None:
        raise SendOrchestratorError(
            "PROVIDER_ATTEMPT_NOT_FOUND",
            "The send operation has no provider attempt to retry.",
        )
    if (
        operation.operation_status == OperationStatus.SENDING_UNCONFIRMED.value
        and latest_attempt.attempt_status == AttemptStatus.PREPARED.value
    ):
        return _PreparedAttempt(
            operation_id=operation.id,
            attempt_id=latest_attempt.id,
            email=None,
            provider_call_required=False,
        )
    if operation.operation_status != OperationStatus.DEFINITIVE_FAILURE.value:
        raise SendOrchestratorError(
            "SEND_OPERATION_NOT_RETRYABLE",
            f"A send operation in {operation.operation_status} cannot be retried.",
        )
    if operation.failure_category not in {
        FailureCategory.TRANSIENT_RETRYABLE.value,
        FailureCategory.QUOTA_EXCEEDED.value,
    }:
        raise SendOrchestratorError(
            "SEND_FAILURE_NOT_RETRYABLE",
            "This provider failure requires a corrected draft instead of a retry.",
        )

    draft = operation.draft_revision
    email = ResendEmail(
        to_email=draft.to_email,
        subject=draft.subject,
        body=draft.rendered_body,
    )
    attempt = ProviderAttempt(
        operation_id=operation.id,
        attempt_number=latest_attempt.attempt_number + 1,
        request_payload_digest=digest_payload(adapter.build_payload(email)),
        attempt_status=AttemptStatus.PREPARED.value,
    )
    operation.operation_status = OperationStatus.SENDING_UNCONFIRMED.value
    operation.final_outcome = None
    operation.failure_category = None
    operation.provider_message_id = None
    db.add(attempt)
    db.flush()
    _audit_send_prepared(db, operation=operation, attempt=attempt, actor=actor)
    return _PreparedAttempt(
        operation_id=operation.id,
        attempt_id=attempt.id,
        email=email,
        provider_call_required=True,
    )


def _prepare_unknown_replay(
    db: Session,
    *,
    adapter: ResendEmailAdapter,
    operation_id: UUID,
    current_time: datetime,
    actor: str = "demo_hr",
) -> _PreparedAttempt:
    operation = db.execute(
        select(LogicalSendOperation)
        .where(LogicalSendOperation.id == operation_id)
        .with_for_update()
    ).scalar_one_or_none()
    if operation is None:
        raise SendOrchestratorError(
            "SEND_OPERATION_NOT_FOUND",
            "The logical send operation no longer exists.",
        )
    latest_attempt = db.execute(
        select(ProviderAttempt)
        .where(ProviderAttempt.operation_id == operation.id)
        .order_by(ProviderAttempt.attempt_number.desc())
        .limit(1)
        .with_for_update()
    ).scalar_one_or_none()
    if latest_attempt is None:
        raise SendOrchestratorError(
            "PROVIDER_ATTEMPT_NOT_FOUND",
            "The send operation has no provider attempt to reconcile.",
        )
    if (
        operation.operation_status == OperationStatus.SENDING_UNCONFIRMED.value
        and latest_attempt.attempt_status == AttemptStatus.PREPARED.value
    ):
        return _PreparedAttempt(
            operation_id=operation.id,
            attempt_id=latest_attempt.id,
            email=None,
            provider_call_required=False,
        )
    if operation.operation_status != OperationStatus.DELIVERY_UNKNOWN.value:
        raise SendOrchestratorError(
            "DELIVERY_UNKNOWN_REQUIRED",
            "Provider reconciliation requires a delivery-unknown operation.",
        )
    created_at = operation.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    normalized_now = current_time
    if normalized_now.tzinfo is None:
        normalized_now = normalized_now.replace(tzinfo=timezone.utc)
    elapsed_seconds = (normalized_now - created_at).total_seconds()
    if elapsed_seconds < 0 or elapsed_seconds > RESEND_IDEMPOTENCY_WINDOW_HOURS * 3600:
        raise SendOrchestratorError(
            "IDEMPOTENCY_WINDOW_EXPIRED",
            "Provider replay is unavailable after 24 hours. Manually verify delivery status.",
        )

    draft = operation.draft_revision
    email = ResendEmail(
        to_email=draft.to_email,
        subject=draft.subject,
        body=draft.rendered_body,
    )
    attempt = ProviderAttempt(
        operation_id=operation.id,
        attempt_number=latest_attempt.attempt_number + 1,
        request_payload_digest=digest_payload(adapter.build_payload(email)),
        attempt_status=AttemptStatus.PREPARED.value,
    )
    operation.operation_status = OperationStatus.SENDING_UNCONFIRMED.value
    operation.final_outcome = None
    operation.failure_category = None
    operation.resolution_mode = ResolutionMode.PROVIDER_IDEMPOTENT_REPLAY.value
    db.add(attempt)
    db.flush()
    _audit_send_prepared(db, operation=operation, attempt=attempt, actor=actor)
    return _PreparedAttempt(
        operation_id=operation.id,
        attempt_id=attempt.id,
        email=email,
        provider_call_required=True,
    )


def _finalize_initial_attempt(
    db: Session,
    *,
    operation_id: UUID,
    attempt_id: UUID,
    provider_result: ResendSendResult,
    actor: str,
) -> None:
    operation = db.execute(
        select(LogicalSendOperation)
        .where(LogicalSendOperation.id == operation_id)
        .with_for_update()
    ).scalar_one_or_none()
    attempt = db.execute(
        select(ProviderAttempt)
        .where(ProviderAttempt.id == attempt_id)
        .with_for_update()
    ).scalar_one_or_none()
    if operation is None or attempt is None:
        raise SendOrchestratorError(
            "SEND_OPERATION_STATE_MISSING",
            "The prepared send operation or provider attempt no longer exists.",
        )
    if attempt.request_payload_digest != provider_result.payload_digest:
        raise SendOrchestratorError(
            "PROVIDER_PAYLOAD_MISMATCH",
            "The provider result does not match the frozen draft payload.",
        )
    if attempt.attempt_status != AttemptStatus.PREPARED.value:
        return

    now = datetime.now(timezone.utc)
    attempt.http_status_code = provider_result.http_status_code
    attempt.provider_message_id = provider_result.provider_message_id
    attempt.error_code = provider_result.error_code
    attempt.error_message = provider_result.error_message
    attempt.latency_ms = provider_result.latency_ms
    attempt.completed_at = now

    operation.provider_message_id = provider_result.provider_message_id
    operation.failure_category = provider_result.failure_category
    draft = operation.draft_revision
    draft.status = DraftStatus.FINALIZED.value

    was_provider_replay = (
        operation.resolution_mode == ResolutionMode.PROVIDER_IDEMPOTENT_REPLAY.value
    )
    if provider_result.outcome == OperationStatus.PROVIDER_ACCEPTED.value:
        attempt.attempt_status = AttemptStatus.ACCEPTED.value
        operation.operation_status = OperationStatus.PROVIDER_ACCEPTED.value
        operation.final_outcome = OperationStatus.PROVIDER_ACCEPTED.value
        if operation.resolution_mode is None:
            operation.resolution_mode = ResolutionMode.AUTOMATIC_SYNC.value
        operation.resolved_at = now
        candidate = db.execute(
            select(Candidate)
            .where(Candidate.id == draft.candidate_id)
            .with_for_update()
        ).scalar_one()
        candidate.communicated_decision = draft.decision
        candidate.communicated_stage = draft.stage
        candidate.communicated_at = now
        _audit_send_finalized(
            db,
            operation=operation,
            attempt=attempt,
            actor=actor,
            outcome=ActionOutcome.SUCCESS,
        )
        if was_provider_replay:
            _audit_delivery_unknown_provider_resolution(
                db,
                operation=operation,
                attempt=attempt,
                actor=actor,
            )
        return

    if provider_result.outcome == OperationStatus.DELIVERY_UNKNOWN.value:
        attempt.attempt_status = AttemptStatus.UNCONFIRMED_TIMEOUT.value
        operation.operation_status = OperationStatus.DELIVERY_UNKNOWN.value
        operation.final_outcome = OperationStatus.DELIVERY_UNKNOWN.value
        _audit_send_finalized(
            db,
            operation=operation,
            attempt=attempt,
            actor=actor,
            outcome=ActionOutcome.UNCONFIRMED,
        )
        return

    attempt.attempt_status = AttemptStatus.DEFINITIVE_FAILURE.value
    if provider_result.failure_category == FailureCategory.VALIDATION_TERMINAL.value:
        operation.operation_status = OperationStatus.FAILED_TERMINAL.value
        operation.final_outcome = OperationStatus.FAILED_TERMINAL.value
    else:
        operation.operation_status = OperationStatus.DEFINITIVE_FAILURE.value
        operation.final_outcome = OperationStatus.DEFINITIVE_FAILURE.value
    _audit_send_finalized(
        db,
        operation=operation,
        attempt=attempt,
        actor=actor,
        outcome=ActionOutcome.FAILURE,
    )


def _audit_send_prepared(
    db: Session,
    *,
    operation: LogicalSendOperation,
    attempt: ProviderAttempt,
    actor: str,
) -> None:
    append_audit_event(
        db,
        event=AuditEvent.SEND_PREPARED,
        entity_type="LOGICAL_SEND_OPERATION",
        entity_id=operation.id,
        application_id=operation.draft_revision.candidate.application_id,
        actor=actor,
        payload={
            "attempt_number": attempt.attempt_number,
            "draft_revision_id": str(operation.draft_revision_id),
            "operation_status": operation.operation_status,
            "provider_name": operation.provider_name,
        },
    )


def _audit_send_finalized(
    db: Session,
    *,
    operation: LogicalSendOperation,
    attempt: ProviderAttempt,
    actor: str,
    outcome: ActionOutcome,
) -> None:
    append_audit_event(
        db,
        event=AuditEvent.SEND_OUTCOME_FINALIZED,
        entity_type="LOGICAL_SEND_OPERATION",
        entity_id=operation.id,
        application_id=operation.draft_revision.candidate.application_id,
        actor=actor,
        outcome=outcome,
        payload={
            "attempt_number": attempt.attempt_number,
            "attempt_status": attempt.attempt_status,
            "failure_category": operation.failure_category,
            "operation_status": operation.operation_status,
            "provider_message_id_present": operation.provider_message_id is not None,
        },
    )


def _audit_delivery_unknown_provider_resolution(
    db: Session,
    *,
    operation: LogicalSendOperation,
    attempt: ProviderAttempt,
    actor: str,
) -> None:
    append_audit_event(
        db,
        event=AuditEvent.DELIVERY_UNKNOWN_RESOLVED,
        entity_type="LOGICAL_SEND_OPERATION",
        entity_id=operation.id,
        application_id=operation.draft_revision.candidate.application_id,
        actor=actor,
        payload={
            "attempt_number": attempt.attempt_number,
            "operation_status": operation.operation_status,
            "resolution": DeliveryUnknownResolution.PROVIDER_ACCEPTED.value,
            "resolution_mode": ResolutionMode.PROVIDER_IDEMPOTENT_REPLAY.value,
        },
    )


def _operation_result(
    session_factory: Callable[[], Session],
    *,
    operation_id: UUID,
    provider_call_performed: bool,
) -> SendExecutionResult:
    with session_factory() as db:
        operation = db.get(LogicalSendOperation, operation_id)
        if operation is None:
            raise SendOrchestratorError(
                "SEND_OPERATION_STATE_MISSING",
                "The logical send operation no longer exists.",
            )
        latest_attempt_id = db.execute(
            select(ProviderAttempt.id)
            .where(ProviderAttempt.operation_id == operation.id)
            .order_by(ProviderAttempt.attempt_number.desc())
            .limit(1)
        ).scalar_one_or_none()
        return SendExecutionResult(
            operation_id=operation.id,
            operation_status=operation.operation_status,
            attempt_id=latest_attempt_id,
            provider_message_id=operation.provider_message_id,
            provider_call_performed=provider_call_performed,
        )


def _assert_draft_can_start_send(draft: DraftRevision) -> None:
    if draft.status not in SENDABLE_DRAFT_STATUSES:
        raise SendOrchestratorError(
            "DRAFT_NOT_READY_TO_SEND",
            f"A draft in {draft.status} status cannot start a send operation.",
        )

    risk_result = draft.risk_check_result or {}
    if risk_result.get("passed") is not True:
        raise SendOrchestratorError(
            "DETERMINISTIC_CHECK_REQUIRED",
            "The deterministic safety check must pass before sending.",
        )
