from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import AuditLog
from app.schemas import AuditLogRead

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])
DbDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    db: DbDep,
) -> list[AuditLog]:
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
