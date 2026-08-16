from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import AuditLog
from app.schemas import AuditLogV1ListResponse


router = APIRouter(prefix="/audit-logs", tags=["v1 Audit"])
DbDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=AuditLogV1ListResponse)
def list_audit_logs(
    db: DbDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    application_id: str | None = None,
    event_name: str | None = None,
) -> AuditLogV1ListResponse:
    query = db.query(AuditLog)
    if application_id:
        query = query.filter(AuditLog.application_id == application_id)
    if event_name:
        query = query.filter(AuditLog.event_name == event_name)
    total = query.count()
    items = (
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return AuditLogV1ListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(ceil(total / page_size), 1),
    )
