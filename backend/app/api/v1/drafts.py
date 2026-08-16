from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Candidate, DraftRevision
from app.schemas import (
    CorrectionDraftRequest,
    DraftCreateRequest,
    DraftReviseRequest,
    DraftRevisionRead,
    DraftRevisionListResponse,
)
from app.services.draft_service import create_decision_correction, generate_draft, revise_draft


router = APIRouter(tags=["v1 Draft Revisions"])
DbDep = Annotated[Session, Depends(get_db)]


@router.post("/drafts", response_model=DraftRevisionRead, status_code=201)
def create_draft(payload: DraftCreateRequest, db: DbDep) -> DraftRevision:
    draft = generate_draft(db, application_id=payload.application_id, actor=payload.actor)
    db.commit()
    db.refresh(draft)
    return draft


@router.patch("/drafts/{draft_revision_id}", response_model=DraftRevisionRead, status_code=201)
def update_draft(
    draft_revision_id: UUID,
    payload: DraftReviseRequest,
    db: DbDep,
) -> DraftRevision:
    draft = revise_draft(
        db,
        draft_revision_id=draft_revision_id,
        editable_content=payload.editable_content,
        subject=payload.subject,
        actor=payload.actor,
    )
    db.commit()
    db.refresh(draft)
    return draft


@router.get("/drafts/{draft_revision_id}", response_model=DraftRevisionRead)
def get_draft(draft_revision_id: UUID, db: DbDep) -> DraftRevision:
    draft = db.get(DraftRevision, draft_revision_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft revision not found.")
    return draft


@router.get("/candidates/{candidate_id}/drafts", response_model=DraftRevisionListResponse)
def list_candidate_drafts(
    candidate_id: int,
    db: DbDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DraftRevisionListResponse:
    if db.get(Candidate, candidate_id) is None:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    query = db.query(DraftRevision).filter(DraftRevision.candidate_id == candidate_id)
    total = query.count()
    items = (
        query.order_by(DraftRevision.revision_number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return DraftRevisionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(ceil(total / page_size), 1),
    )


@router.post(
    "/candidates/{candidate_id}/correction-drafts",
    response_model=DraftRevisionRead,
    status_code=201,
)
def create_correction(
    candidate_id: int,
    payload: CorrectionDraftRequest,
    db: DbDep,
) -> DraftRevision:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    draft = create_decision_correction(
        db,
        application_id=candidate.application_id,
        new_decision=payload.new_decision,
        rationale=payload.rationale,
        actor=payload.actor,
    )
    db.commit()
    db.refresh(draft)
    return draft
