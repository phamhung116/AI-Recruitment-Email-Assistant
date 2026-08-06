from datetime import datetime, timezone
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.constants.auditActions import UPDATE_CANDIDATE_STATUS
from app.constants.messages import CANDIDATE_NOT_FOUND_MESSAGE
from app.db.database import get_db
from app.models import Candidate, EmailHistory, EmailQueue
from app.schemas import (
    BulkActionResult,
    BulkCandidateDelete,
    BulkCandidateStatusUpdate,
    CandidateFilterOptions,
    CandidateListResponse,
    CandidateRead,
    CandidateStatusUpdate,
    CandidateUpdate,
    ImportPreviewResult,
    ImportResult,
)
from app.services.audit import log_action
from app.services.excelImport import import_candidates_from_excel, preview_candidates_from_excel

router = APIRouter(prefix="/candidates", tags=["Candidates"])
DbDep = Annotated[Session, Depends(get_db)]


@router.post("/import", response_model=ImportResult)
async def import_candidates(
    db: DbDep,
    file: UploadFile = File(...),
) -> ImportResult:
    return await import_candidates_from_excel(db, file)


@router.post("/import/preview", response_model=ImportPreviewResult)
async def preview_import_candidates(
    db: DbDep,
    file: UploadFile = File(...),
) -> ImportPreviewResult:
    return await preview_candidates_from_excel(db, file)


SORTABLE_COLUMNS = {
    "full_name": Candidate.full_name,
    "email": Candidate.email,
    "position": Candidate.position,
    "stage": Candidate.stage,
    "status": Candidate.status,
    "interview_time": Candidate.interview_time,
    "created_at": Candidate.created_at,
    "updated_at": Candidate.updated_at,
    "status_updated_at": Candidate.status_updated_at,
}


@router.get("", response_model=CandidateListResponse)
def list_candidates(
    db: DbDep,
    search: str | None = None,
    position: str | None = None,
    stage: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "updated_at",
    sort_order: str = "desc",
) -> CandidateListResponse:
    query = db.query(Candidate)
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

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

    total = query.count()
    if sort_by == "full_name":
        sorted_candidates = sorted(
            query.all(),
            key=lambda candidate: vietnamese_given_name_sort_key(candidate.full_name),
            reverse=sort_order != "asc",
        )
        start_index = (page - 1) * page_size
        candidates = sorted_candidates[start_index:start_index + page_size]
    else:
        sort_column = SORTABLE_COLUMNS.get(sort_by, Candidate.updated_at)
        order_expression = sort_column.asc() if sort_order == "asc" else sort_column.desc()
        candidates = (
            query.order_by(order_expression, Candidate.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

    return CandidateListResponse(
        items=candidates,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(ceil(total / page_size), 1),
    )


@router.patch("/{candidate_id}/status", response_model=CandidateRead)
def update_candidate_status(
    db: DbDep,
    candidate_id: int,
    payload: CandidateStatusUpdate,
) -> Candidate:
    candidate = find_candidate_or_raise(db, candidate_id)
    apply_candidate_status_change(db, candidate, payload.status, payload.actor)
    db.commit()
    db.refresh(candidate)

    return candidate


@router.post("/bulk/status", response_model=BulkActionResult)
def bulk_update_candidate_status(
    db: DbDep,
    payload: BulkCandidateStatusUpdate,
) -> BulkActionResult:
    candidates = db.query(Candidate).filter(Candidate.id.in_(payload.candidate_ids)).all()

    for candidate in candidates:
        apply_candidate_status_change(db, candidate, payload.status, payload.actor)

    db.commit()

    return BulkActionResult(affected=len(candidates))


@router.post("/bulk/delete", response_model=BulkActionResult)
def bulk_delete_candidates(
    db: DbDep,
    payload: BulkCandidateDelete,
) -> BulkActionResult:
    candidate_ids = list(set(payload.candidate_ids))
    candidates = db.query(Candidate).filter(Candidate.id.in_(candidate_ids)).all()
    existing_ids = [candidate.id for candidate in candidates]

    if not existing_ids:
        return BulkActionResult(affected=0)

    db.query(EmailQueue).filter(EmailQueue.candidate_id.in_(existing_ids)).delete(synchronize_session=False)
    db.query(EmailHistory).filter(EmailHistory.candidate_id.in_(existing_ids)).delete(synchronize_session=False)
    db.query(Candidate).filter(Candidate.id.in_(existing_ids)).delete(synchronize_session=False)
    log_action(
        db=db,
        action="delete_candidate",
        entity_type="candidate",
        actor=payload.actor,
        metadata={"candidate_ids": existing_ids},
    )
    db.commit()

    return BulkActionResult(affected=len(existing_ids))


@router.get("/filter-options", response_model=CandidateFilterOptions)
def get_candidate_filter_options(db: DbDep) -> CandidateFilterOptions:
    return CandidateFilterOptions(
        positions=get_distinct_candidate_values(db, Candidate.position),
        stages=get_distinct_candidate_values(db, Candidate.stage),
        statuses=get_distinct_candidate_values(db, Candidate.status),
    )


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
        candidate.status_updated_at = datetime.now(timezone.utc)
        candidate.status_updated_by = "demo_hr"
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


def apply_candidate_status_change(
    db: Session,
    candidate: Candidate,
    status: str,
    actor: str,
) -> None:
    previous_status = candidate.status
    candidate.status = status
    candidate.status_updated_at = datetime.now(timezone.utc)
    candidate.status_updated_by = actor

    if status != previous_status:
        log_action(
            db=db,
            action=UPDATE_CANDIDATE_STATUS,
            entity_type="candidate",
            entity_id=candidate.id,
            actor=actor,
            metadata={
                "from": previous_status,
                "to": status,
            },
        )


def vietnamese_given_name_sort_key(full_name: str) -> tuple[str, str]:
    name_parts = full_name.strip().split()
    given_name = name_parts[-1].lower() if name_parts else ""

    return given_name, full_name.lower()


def get_distinct_candidate_values(db: Session, column) -> list[str]:
    values = db.query(column).filter(column.isnot(None)).distinct().order_by(column.asc()).all()

    return [value for (value,) in values if value]


def find_candidate_or_raise(
    db: Session,
    candidate_id: int,
) -> Candidate:
    candidate = db.get(Candidate, candidate_id)

    if not candidate:
        raise HTTPException(status_code=404, detail=CANDIDATE_NOT_FOUND_MESSAGE)

    return candidate
