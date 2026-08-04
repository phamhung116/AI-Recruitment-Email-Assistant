from datetime import datetime
from io import BytesIO

from fastapi import HTTPException, UploadFile
from openpyxl.utils.exceptions import InvalidFileException
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models import Candidate
from app.schemas import ImportResult


async def import_candidates_from_excel(
    db: Session,
    file: UploadFile,
) -> ImportResult:
    if file.filename and not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Please upload a .xlsx Excel file.")

    content = await file.read()
    try:
        workbook = load_workbook(BytesIO(content))
    except InvalidFileException as error:
        raise HTTPException(status_code=400, detail="Invalid Excel file format.") from error

    sheet = workbook.active
    headers = [
        str(cell.value).strip() if cell.value else ""
        for cell in next(sheet.iter_rows(min_row=1, max_row=1))
    ]
    normalized_headers = [
        normalize_header(header)
        for header in headers
    ]
    imported_count = 0
    skipped_count = 0
    errors: list[str] = []
    existing_emails = {
        candidate.email.lower()
        for candidate in db.query(Candidate).all()
        if candidate.email
    }

    for row_index, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        payload = build_row_payload(normalized_headers, row)
        email = to_optional_string(payload.get("email"))

        if not payload.get("full_name"):
            skipped_count += 1
            errors.append(f"Row {row_index}: missing full_name")
            continue

        if email and email.lower() in existing_emails:
            skipped_count += 1
            errors.append(f"Row {row_index}: duplicate email {email}")
            continue

        try:
            db.add(create_candidate_from_payload(payload))
            if email:
                existing_emails.add(email.lower())
            imported_count += 1
        except ValueError as error:
            skipped_count += 1
            errors.append(f"Row {row_index}: {error}")

    db.commit()

    return ImportResult(
        imported=imported_count,
        skipped=skipped_count,
        errors=errors,
    )


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
        status=to_optional_string(payload.get("status")) or "PENDING",
        interview_time=to_optional_datetime(payload.get("interview_time")),
        interviewer=to_optional_string(payload.get("interviewer")),
        note=to_optional_string(payload.get("note")),
    )


def normalize_header(
    header: str,
) -> str:
    return header.strip().lower().replace(" ", "_")


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
