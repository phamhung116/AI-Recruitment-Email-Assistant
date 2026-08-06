from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy.orm import Session, joinedload

from app.constants.messages import EMAIL_QUEUE_NOT_FOUND_MESSAGE
from app.db.database import get_db
from app.models import EmailQueue
from app.schemas import EmailQueueRead, EmailQueueUpdate, GenerateEmailDraftRequest
from app.services.draft_review_queue import REVIEW_METADATA_KEY, review_metadata
from app.services.email_workflow import approve_email, cancel_email, generate_email_draft, send_email, update_email_draft
from app.services.review_progress import get_redis_client, read_review_progress

router = APIRouter(tags=["Email Queue"])
DbDep = Annotated[Session, Depends(get_db)]


def get_review_redis() -> Redis:
    return get_redis_client()


ReviewRedisDep = Annotated[Redis, Depends(get_review_redis)]


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
    review_redis: ReviewRedisDep,
    queue_id: int,
) -> EmailQueueRead:
    item = find_queue_item_or_raise(db, queue_id)
    response = EmailQueueRead.model_validate(item)
    metadata = review_metadata(item)
    draft_version = metadata.get("draft_version")
    if not isinstance(draft_version, int):
        return response

    try:
        progress = read_review_progress(
            review_redis,
            queue_id=item.id,
            draft_version=draft_version,
        )
    except (RedisError, ValueError, TypeError):
        return response

    if not progress or not isinstance(progress.get("status"), str):
        return response

    risk_result = dict(response.risk_check_result or {})
    async_review = risk_result.get(REVIEW_METADATA_KEY)
    async_review = dict(async_review) if isinstance(async_review, dict) else {}
    async_review.update(
        {
            "status": progress["status"],
            "draft_version": draft_version,
            "updated_at": progress.get("updated_at"),
        }
    )
    risk_result[REVIEW_METADATA_KEY] = async_review
    response.risk_check_result = risk_result
    return response


@router.patch("/email-queue/{queue_id}", response_model=EmailQueueRead)
def update_email_queue(
    db: DbDep,
    queue_id: int,
    payload: EmailQueueUpdate,
) -> EmailQueue:
    values = payload.model_dump(exclude_unset=True)
    return update_email_draft(
        db=db,
        queue_id=queue_id,
        subject=values.get("subject"),
        body=values.get("body"),
    )


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
