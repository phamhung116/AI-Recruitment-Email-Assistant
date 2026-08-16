from collections.abc import Callable
from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.adapters.resend_adapter import ResendEmailAdapter
from app.api.v1.dependencies import get_resend_adapter, get_session_factory
from app.db.database import get_db
from app.models import DraftRevision, LogicalSendOperation
from app.schemas import (
    DeliveryResolutionRequest,
    SendConfirmationRequest,
    SendOperationListResponse,
    SendOperationRead,
)
from app.services.send_orchestrator import (
    DeliveryUnknownResolution,
    SendOrchestratorError,
    execute_initial_send,
    reconcile_delivery_unknown_via_provider,
    resolve_delivery_unknown,
    retry_definitive_failure,
)


router = APIRouter(tags=["v1 Send Operations"])
DbDep = Annotated[Session, Depends(get_db)]
AdapterDep = Annotated[ResendEmailAdapter, Depends(get_resend_adapter)]
SessionFactoryDep = Annotated[Callable[[], Session], Depends(get_session_factory)]


@router.post("/drafts/{draft_revision_id}/send", response_model=SendOperationRead)
def send_draft(
    draft_revision_id: UUID,
    payload: SendConfirmationRequest,
    adapter: AdapterDep,
    session_factory: SessionFactoryDep,
    db: DbDep,
) -> LogicalSendOperation:
    _require_send_confirmation(payload.confirmation_acknowledged)
    result = execute_initial_send(
        session_factory,
        adapter=adapter,
        draft_revision_id=draft_revision_id,
        actor=payload.actor,
    )
    return _load_operation(db, result.operation_id)


@router.post("/send-operations/{operation_id}/retry", response_model=SendOperationRead)
def retry_send(
    operation_id: UUID,
    payload: SendConfirmationRequest,
    adapter: AdapterDep,
    session_factory: SessionFactoryDep,
    db: DbDep,
) -> LogicalSendOperation:
    _require_send_confirmation(payload.confirmation_acknowledged)
    result = retry_definitive_failure(
        session_factory,
        adapter=adapter,
        operation_id=operation_id,
        actor=payload.actor,
    )
    return _load_operation(db, result.operation_id)


@router.post("/send-operations/{operation_id}/reconcile", response_model=SendOperationRead)
def reconcile_send(
    operation_id: UUID,
    payload: SendConfirmationRequest,
    adapter: AdapterDep,
    session_factory: SessionFactoryDep,
    db: DbDep,
) -> LogicalSendOperation:
    _require_send_confirmation(payload.confirmation_acknowledged)
    result = reconcile_delivery_unknown_via_provider(
        session_factory,
        adapter=adapter,
        operation_id=operation_id,
        actor=payload.actor,
    )
    return _load_operation(db, result.operation_id)


@router.post("/send-operations/{operation_id}/resolve", response_model=SendOperationRead)
def manually_resolve_send(
    operation_id: UUID,
    payload: DeliveryResolutionRequest,
    db: DbDep,
) -> LogicalSendOperation:
    try:
        resolution = DeliveryUnknownResolution(payload.resolution)
    except ValueError as error:
        raise SendOrchestratorError(
            "DELIVERY_RESOLUTION_UNSUPPORTED",
            "Resolution must be PROVIDER_ACCEPTED or PROVIDER_NOT_RECEIVED.",
        ) from error
    resolve_delivery_unknown(
        db,
        operation_id=operation_id,
        resolution=resolution,
        rationale=payload.rationale,
        resolved_by=payload.actor,
        warning_acknowledged=payload.warning_acknowledged,
    )
    db.commit()
    return _load_operation(db, operation_id)


@router.get("/send-operations", response_model=SendOperationListResponse)
def list_send_operations(
    db: DbDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status: str | None = None,
    application_id: str | None = None,
) -> SendOperationListResponse:
    query = db.query(LogicalSendOperation).options(selectinload(LogicalSendOperation.attempts))
    if status:
        query = query.filter(LogicalSendOperation.operation_status == status)
    if application_id:
        query = query.join(LogicalSendOperation.draft_revision).filter(
            DraftRevision.candidate.has(application_id=application_id)
        )
    total = query.count()
    items = (
        query.order_by(LogicalSendOperation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return SendOperationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(ceil(total / page_size), 1),
    )


@router.get("/send-operations/{operation_id}", response_model=SendOperationRead)
def get_send_operation(operation_id: UUID, db: DbDep) -> LogicalSendOperation:
    return _load_operation(db, operation_id)


def _load_operation(db: Session, operation_id: UUID) -> LogicalSendOperation:
    operation = (
        db.query(LogicalSendOperation)
        .options(selectinload(LogicalSendOperation.attempts))
        .filter(LogicalSendOperation.id == operation_id)
        .one_or_none()
    )
    if operation is None:
        raise HTTPException(status_code=404, detail="Send operation not found.")
    return operation


def _require_send_confirmation(acknowledged: bool) -> None:
    if not acknowledged:
        raise SendOrchestratorError(
            "SEND_CONFIRMATION_REQUIRED",
            "Explicit HR confirmation is required before sending a real email.",
        )
