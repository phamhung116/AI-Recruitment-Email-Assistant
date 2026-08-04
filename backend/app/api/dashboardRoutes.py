from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Candidate, EmailQueue, QueueStatus
from app.schemas import DashboardStats

router = APIRouter()
DbDep = Annotated[Session, Depends(get_db)]


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    db: DbDep,
) -> DashboardStats:
    pending_statuses = [
        QueueStatus.DRAFT.value,
        QueueStatus.PENDING_APPROVAL.value,
        QueueStatus.APPROVED.value,
    ]

    return DashboardStats(
        total_candidates=db.query(func.count(Candidate.id)).scalar() or 0,
        pending_emails=db.query(func.count(EmailQueue.id)).filter(EmailQueue.status.in_(pending_statuses)).scalar() or 0,
        sent_emails=db.query(func.count(EmailQueue.id)).filter(EmailQueue.status == QueueStatus.SENT.value).scalar() or 0,
        failed_emails=db.query(func.count(EmailQueue.id)).filter(EmailQueue.status == QueueStatus.FAILED.value).scalar() or 0,
    )
