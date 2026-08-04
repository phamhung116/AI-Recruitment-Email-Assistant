from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.constants.auditActions import UPDATE_CANDIDATE_STATUS
from app.constants.messages import CANDIDATE_NOT_FOUND_MESSAGE
from app.db.database import get_db
from app.models import Candidate
from app.schemas import CandidateRead, CandidateUpdate, ImportResult
from app.services.audit import log_action
from app.services.excelImport import import_candidates_from_excel

router = APIRouter(prefix="/candidates", tags=["Candidates"])
DbDep = Annotated[Session, Depends(get_db)]


@router.post("/import", response_model=ImportResult)
async def import_candidates(
    db: DbDep,
    file: UploadFile = File(...),
) -> ImportResult:
    return await import_candidates_from_excel(db, file)


@router.get("", response_model=list[CandidateRead])
def list_candidates(
    db: DbDep,
    search: str | None = None,
    position: str | None = None,
    stage: str | None = None,
    status: str | None = None,
) -> list[Candidate]:
    query = db.query(Candidate)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Candidate.full_name.ilike(search_pattern))
            | (Candidate.email.ilike(search_pattern))
        )

    if position:
        query = query.filter(Candidate.position == position)

    if stage:
        query = query.filter(Candidate.stage == stage)

    if status:
        query = query.filter(Candidate.status == status)

    return query.order_by(Candidate.created_at.desc()).all()


@router.get("/{candidate_id}", response_model=CandidateRead)
def get_candidate(
    db: DbDep,
    candidate_id: int,
) -> Candidate:
    return find_candidate_or_raise(db, candidate_id)


@router.patch("/{candidate_id}", response_model=CandidateRead)
def update_candidate(
    db: DbDep,
    candidate_id: int,
    payload: CandidateUpdate,
) -> Candidate:
    candidate = find_candidate_or_raise(db, candidate_id)
    previous_status = candidate.status

    for field_name, value in payload.model_dump(exclude_unset=True).items():
        setattr(candidate, field_name, value)

    if payload.status and payload.status != previous_status:
        log_action(
            db=db,
            action=UPDATE_CANDIDATE_STATUS,
            entity_type="candidate",
            entity_id=candidate.id,
            metadata={
                "from": previous_status,
                "to": payload.status,
            },
        )

    db.commit()
    db.refresh(candidate)

    return candidate


def find_candidate_or_raise(
    db: Session,
    candidate_id: int,
) -> Candidate:
    candidate = db.get(Candidate, candidate_id)

    if not candidate:
        raise HTTPException(status_code=404, detail=CANDIDATE_NOT_FOUND_MESSAGE)

    return candidate
