from math import ceil
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import Candidate
from app.schemas import CandidateV1ListResponse, CandidateV1Read, ImportPreviewResult, ImportResult
from app.services.excelImport import import_candidates_from_excel, preview_candidates_from_excel


router = APIRouter(prefix="/candidates", tags=["v1 Candidates"])
DbDep = Annotated[Session, Depends(get_db)]


@router.post("/import/preview", response_model=ImportPreviewResult)
async def preview_import(db: DbDep, file: UploadFile = File(...)) -> ImportPreviewResult:
    return await preview_candidates_from_excel(db, file)


@router.post("/import", response_model=ImportResult)
async def import_candidates(db: DbDep, file: UploadFile = File(...)) -> ImportResult:
    return await import_candidates_from_excel(db, file)


@router.get("", response_model=CandidateV1ListResponse)
def list_candidates(
    db: DbDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = None,
    stage: str | None = None,
    status: str | None = None,
    sort: Literal["full_name", "created_at", "updated_at", "status_updated_at"] = "updated_at",
    direction: Literal["asc", "desc"] = "desc",
) -> CandidateV1ListResponse:
    query = db.query(Candidate)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(Candidate.full_name.ilike(pattern), Candidate.application_id.ilike(pattern))
        )
    if stage:
        query = query.filter(Candidate.stage == stage)
    if status:
        query = query.filter(Candidate.status == status)

    total = query.count()
    if sort == "full_name":
        rows = sorted(
            query.all(),
            key=lambda candidate: _given_name_key(candidate.full_name),
            reverse=direction == "desc",
        )[(page - 1) * page_size : page * page_size]
    else:
        column = getattr(Candidate, sort)
        order = column.asc() if direction == "asc" else column.desc()
        rows = query.order_by(order, Candidate.id.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return CandidateV1ListResponse(
        items=rows,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(ceil(total / page_size), 1),
    )


@router.get("/{candidate_id}", response_model=CandidateV1Read)
def get_candidate(candidate_id: int, db: DbDep) -> Candidate:
    candidate = db.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return candidate


def _given_name_key(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().casefold().split()
    return (parts[-1] if parts else "", " ".join(parts))
