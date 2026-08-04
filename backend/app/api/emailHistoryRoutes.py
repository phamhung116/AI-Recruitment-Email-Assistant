from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models import EmailHistory
from app.schemas import EmailHistoryRead

router = APIRouter(prefix="/email-history", tags=["Email History"])
DbDep = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[EmailHistoryRead])
def list_email_history(
    db: DbDep,
    candidate_id: int | None = None,
) -> list[EmailHistory]:
    query = db.query(EmailHistory).options(joinedload(EmailHistory.candidate))

    if candidate_id:
        query = query.filter(EmailHistory.candidate_id == candidate_id)

    return query.order_by(EmailHistory.sent_at.desc()).all()
