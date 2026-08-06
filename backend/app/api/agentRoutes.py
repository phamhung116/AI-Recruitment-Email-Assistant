from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.agent import AgentReviewResult, ReviewQueuedDraftRequest
from app.services.agent_review import review_queue_draft


router = APIRouter(prefix="/api/v1/agent", tags=["Agent Review"])
DbDep = Annotated[Session, Depends(get_db)]


@router.post("/review-draft", response_model=AgentReviewResult)
def review_draft(
    db: DbDep,
    payload: ReviewQueuedDraftRequest,
) -> AgentReviewResult:
    return review_queue_draft(
        db=db,
        queue_id=payload.queue_id,
        actor=payload.actor,
    )
