from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.constants.messages import EMAIL_QUEUE_NOT_FOUND_MESSAGE
from app.db.database import get_db
from app.models import EmailQueue, QueueStatus
from app.schemas import EmailQueueRead, EmailQueueUpdate, GenerateEmailDraftRequest
from app.services.email_workflow import approve_email, cancel_email, generate_email_draft, send_email

router = APIRouter(tags=["Email Queue"])
DbDep = Annotated[Session, Depends(get_db)]


@router.post("/email-drafts/generate", response_model=EmailQueueRead)
def generate_draft(
    db: DbDep,
    payload: GenerateEmailDraftRequest,
) -> EmailQueue:
    return generate_email_draft(
        db=db,
        candidate_id=payload.candidate_id,
        requested_email_type=payload.email_type,
        created_by=payload.created_by,
    )


@router.get("/email-queue", response_model=list[EmailQueueRead])
def list_email_queue(
    db: DbDep,
    status: str | None = None,
) -> list[EmailQueue]:
    query = db.query(EmailQueue).options(joinedload(EmailQueue.candidate))

    if status:
        query = query.filter(EmailQueue.status == status)

    return query.order_by(EmailQueue.created_at.desc()).all()


@router.get("/email-queue/{queue_id}", response_model=EmailQueueRead)
def get_email_queue(
    db: DbDep,
    queue_id: int,
) -> EmailQueue:
    return find_queue_item_or_raise(db, queue_id)


@router.patch("/email-queue/{queue_id}", response_model=EmailQueueRead)
def update_email_queue(
    db: DbDep,
    queue_id: int,
    payload: EmailQueueUpdate,
) -> EmailQueue:
    item = find_queue_item_or_raise(db, queue_id)

    if item.status == QueueStatus.SENT.value:
        raise HTTPException(status_code=400, detail="Cannot edit sent email.")

    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field_name, value)

    db.commit()
    db.refresh(item)

    return item


@router.post("/email-queue/{queue_id}/approve", response_model=EmailQueueRead)
def approve_queue_item(
    db: DbDep,
    queue_id: int,
) -> EmailQueue:
    return approve_email(db, queue_id)


@router.post("/email-queue/{queue_id}/send", response_model=EmailQueueRead)
def send_queue_item(
    db: DbDep,
    queue_id: int,
) -> EmailQueue:
    return send_email(db, queue_id)


@router.post("/email-queue/{queue_id}/cancel", response_model=EmailQueueRead)
def cancel_queue_item(
    db: DbDep,
    queue_id: int,
) -> EmailQueue:
    return cancel_email(db, queue_id)


def find_queue_item_or_raise(
    db: Session,
    queue_id: int,
) -> EmailQueue:
    item = (
        db.query(EmailQueue)
        .options(joinedload(EmailQueue.candidate))
        .filter(EmailQueue.id == queue_id)
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail=EMAIL_QUEUE_NOT_FOUND_MESSAGE)

    return item
