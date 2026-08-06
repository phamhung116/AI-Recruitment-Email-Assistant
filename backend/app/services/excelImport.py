from datetime import datetime
from io import BytesIO
from zipfile import BadZipFile

from fastapi import HTTPException, UploadFile
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy.orm import Session

from app.models import Candidate, CandidateStatus
from app.schemas import ImportPreviewResult, ImportPreviewRow, ImportResult


async def preview_candidates_from_excel(
    db: Session,
    file: UploadFile,
) -> ImportPreviewResult:
    content = await read_excel_content(file)
    preview_rows = build_preview_rows(db, content)
    valid_rows = [row for row in preview_rows if row.is_valid]

    return ImportPreviewResult(
        total_rows=len(preview_rows),
        valid_rows=len(valid_rows),
        invalid_rows=len(preview_rows) - len(valid_rows),
        rows=preview_rows,
    )


async def import_candidates_from_excel(
    db: Session,
    file: UploadFile,
) -> ImportResult:
    content = await read_excel_content(file)
    preview_rows = build_preview_rows(db, content)
    imported_count = 0
    errors: list[str] = []

    for row in preview_rows:
        if not row.is_valid:
            errors.append(f"Row {row.row_number}: {row.reason}")
            continue

        db.add(create_candidate_from_payload(row.candidate))
        imported_count += 1

    db.commit()

    return ImportResult(
        imported=imported_count,
        skipped=len(preview_rows) - imported_count,
        errors=errors,
    )


async def read_excel_content(file: UploadFile) -> bytes:
    if file.filename and not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Please upload a .xlsx Excel file.")

    return await file.read()


def build_preview_rows(
    db: Session,
    content: bytes,
) -> list[ImportPreviewRow]:
    workbook = open_workbook(content)
    sheet = workbook.active
    header_row = next(sheet.iter_rows(min_row=1, max_row=1), None)

    if not header_row:
        raise HTTPException(status_code=400, detail="Excel file is empty.")

    headers = [
        str(cell.value).strip() if cell.value else ""
        for cell in header_row
    ]
    normalized_headers = [
        normalize_header(header)
        for header in headers
    ]
    existing_emails = {
        candidate.email.lower()
        for candidate in db.query(Candidate).all()
        if candidate.email
    }
    preview_rows: list[ImportPreviewRow] = []
    seen_file_emails: set[str] = set()

    for row_index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        if is_empty_row(row):
            continue

        raw_payload = build_row_payload(normalized_headers, row)
        candidate_payload, errors = validate_candidate_payload(raw_payload)
        email = candidate_payload.get("email")

        if email:
            normalized_email = str(email).lower()

            if normalized_email in existing_emails:
                errors.append(f"Duplicate email already exists: {email}")
            elif normalized_email in seen_file_emails:
                errors.append(f"Duplicate email in this file: {email}")
            else:
                seen_file_emails.add(normalized_email)

        preview_rows.append(
            ImportPreviewRow(
                row_number=row_index,
                is_valid=len(errors) == 0,
                reason="; ".join(errors) if errors else None,
                candidate=candidate_payload,
            )
        )

    return preview_rows


def open_workbook(content: bytes):
    try:
        return load_workbook(BytesIO(content))
    except (BadZipFile, InvalidFileException) as error:
        raise HTTPException(status_code=400, detail="Invalid Excel file format.") from error


def validate_candidate_payload(
    payload: dict[str, object],
) -> tuple[dict[str, object], list[str]]:
    errors: list[str] = []
    full_name = to_optional_string(payload.get("full_name"))
    status = normalize_status(payload.get("status"))
    interview_time = None

    if not full_name:
        errors.append("Missing full_name")

    if status is None:
        errors.append(f"Invalid status: {payload.get('status')}")

    try:
        interview_time = to_optional_datetime(payload.get("interview_time"))
    except ValueError:
        errors.append(f"Invalid interview_time: {payload.get('interview_time')}")

    candidate_payload: dict[str, object] = {
        "full_name": full_name or "",
        "email": to_optional_string(payload.get("email")),
        "phone": to_optional_string(payload.get("phone")),
        "position": to_optional_string(payload.get("position")),
        "stage": to_optional_string(payload.get("stage")) or "NEW",
        "status": status or CandidateStatus.PENDING.value,
        "interview_time": interview_time,
        "interviewer": to_optional_string(payload.get("interviewer")),
        "note": to_optional_string(payload.get("note")),
    }

    return candidate_payload, errors


def build_row_payload(
    headers: list[str],
    row: tuple[object, ...],
) -> dict[str, object]:
    return {
        headers[index]: row[index]
        for index in range(min(len(headers), len(row)))
        if headers[index]
    }


def create_candidate_from_payload(
    payload: dict[str, object],
) -> Candidate:
    return Candidate(
        full_name=str(payload.get("full_name")).strip(),
        email=to_optional_string(payload.get("email")),
        phone=to_optional_string(payload.get("phone")),
        position=to_optional_string(payload.get("position")),
        stage=to_optional_string(payload.get("stage")) or "NEW",
        status=normalize_status(payload.get("status")) or CandidateStatus.PENDING.value,
        interview_time=to_optional_datetime(payload.get("interview_time")),
        interviewer=to_optional_string(payload.get("interviewer")),
        note=to_optional_string(payload.get("note")),
    )


def normalize_header(
    header: str,
) -> str:
    return header.strip().lower().replace(" ", "_")


def normalize_status(value: object) -> str | None:
    raw_status = to_optional_string(value)

    if not raw_status:
        return CandidateStatus.PENDING.value

    normalized_status = raw_status.strip().upper().replace("-", "_").replace(" ", "_")
    valid_statuses = {status.value for status in CandidateStatus}

    return normalized_status if normalized_status in valid_statuses else None


def to_optional_string(
    value: object,
) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def to_optional_datetime(
    value: object,
) -> datetime | None:
    if isinstance(value, datetime):
        return value

    if isinstance(value, str) and value.strip():
        return datetime.fromisoformat(value.strip())

    return None


def is_empty_row(row: tuple[object, ...]) -> bool:
    return all(value is None or str(value).strip() == "" for value in row)
