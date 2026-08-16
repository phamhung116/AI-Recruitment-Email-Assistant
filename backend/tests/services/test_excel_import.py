from __future__ import annotations

import asyncio
from collections.abc import Iterator
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base
from app.models import Candidate
from app.services.excelImport import (
    build_preview_rows,
    import_candidates_from_excel,
)


HEADERS = [
    "Application ID",
    "Candidate Name",
    "Email",
    "Stage",
    "Status",
    "Position",
    "Phone",
    "Interview Time",
    "Interviewer",
    "Note",
]


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def workbook_bytes(headers: list[str], rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def valid_row(application_id: str = "APP-2026-001", email: str = "hr@example.com") -> list[object]:
    return [
        application_id,
        "Nguyen Van A",
        email,
        "cv screening",
        "pass cv",
        None,
        None,
        None,
        None,
        None,
    ]


def test_missing_required_header_rejects_the_file(db: Session) -> None:
    content = workbook_bytes(
        [header for header in HEADERS if header != "Application ID"],
        [["Nguyen Van A", "hr@example.com", "CV_SCREENING", "PASS_CV"]],
    )

    with pytest.raises(HTTPException) as caught:
        build_preview_rows(db, content)

    assert caught.value.status_code == 400
    assert "CANDIDATE_HEADER_INVALID" in str(caught.value.detail)
    assert "Application ID" in str(caught.value.detail)


@pytest.mark.parametrize("name_header", ["Candidate Name", "Name", "Full Name"])
def test_candidate_name_header_aliases_are_supported(db: Session, name_header: str) -> None:
    headers = [name_header if header == "Candidate Name" else header for header in HEADERS]

    preview = build_preview_rows(db, workbook_bytes(headers, [valid_row()]))

    assert preview[0].is_valid is True
    assert preview[0].candidate == {
        "application_id": "APP-2026-001",
        "full_name": "Nguyen Van A",
        "email": "hr@example.com",
        "phone": None,
        "position": None,
        "stage": "CV_SCREENING",
        "status": "PASS_CV",
        "interview_time": None,
        "interviewer": None,
        "note": None,
    }


def test_missing_required_values_are_reported_without_defaults(db: Session) -> None:
    row = valid_row()
    row[0] = None
    row[2] = None
    row[3] = None
    row[4] = None

    preview = build_preview_rows(db, workbook_bytes(HEADERS, [row]))

    assert preview[0].is_valid is False
    assert preview[0].reason == (
        "CANDIDATE_REQUIRED_VALUE_MISSING: Missing required value(s): "
        "Application ID, Email, Stage, Status"
    )
    assert preview[0].candidate["stage"] == ""
    assert preview[0].candidate["status"] == ""


def test_invalid_required_formats_are_rejected(db: Session) -> None:
    row = valid_row(email="not-an-email")
    row[3] = "PHONE_SCREEN"
    row[4] = "HIRED"
    row[7] = "tomorrow afternoon"

    preview = build_preview_rows(db, workbook_bytes(HEADERS, [row]))

    assert preview[0].is_valid is False
    assert preview[0].reason is not None
    assert preview[0].reason.count("CANDIDATE_FIELD_INVALID") == 4
    assert "Invalid Email" in preview[0].reason
    assert "Unsupported Stage" in preview[0].reason
    assert "Unsupported Status" in preview[0].reason
    assert "Invalid Interview Time" in preview[0].reason


def test_application_id_longer_than_database_contract_is_rejected(db: Session) -> None:
    preview = build_preview_rows(
        db,
        workbook_bytes(HEADERS, [valid_row("A" * 65)]),
    )

    assert preview[0].is_valid is False
    assert preview[0].reason == (
        "CANDIDATE_FIELD_INVALID: application_id exceeds 64 characters"
    )


def test_existing_application_id_is_rejected(db: Session) -> None:
    db.add(
        Candidate(
            application_id="APP-2026-001",
            full_name="Existing Candidate",
            email="existing@example.com",
            stage="CV_SCREENING",
            status="PENDING",
        )
    )
    db.commit()

    preview = build_preview_rows(db, workbook_bytes(HEADERS, [valid_row()]))

    assert preview[0].is_valid is False
    assert preview[0].reason == (
        "DUPLICATE_APPLICATION_ID: Application ID already exists: APP-2026-001"
    )


def test_every_repeated_application_id_in_one_file_is_rejected(db: Session) -> None:
    content = workbook_bytes(
        HEADERS,
        [
            valid_row("APP-DUPLICATE", "first@example.com"),
            valid_row("APP-DUPLICATE", "second@example.com"),
        ],
    )

    preview = build_preview_rows(db, content)

    assert len(preview) == 2
    assert all(row.is_valid is False for row in preview)
    assert all("DUPLICATE_APPLICATION_ID" in (row.reason or "") for row in preview)


def test_same_email_is_allowed_for_distinct_applications(db: Session) -> None:
    content = workbook_bytes(
        HEADERS,
        [
            valid_row("APP-ROLE-A", "candidate@example.com"),
            valid_row("APP-ROLE-B", "candidate@example.com"),
        ],
    )

    preview = build_preview_rows(db, content)

    assert [row.is_valid for row in preview] == [True, True]


def test_preview_is_read_only_and_import_persists_only_valid_rows(db: Session) -> None:
    invalid_row = valid_row("APP-INVALID", "invalid-email")
    content = workbook_bytes(HEADERS, [valid_row("APP-VALID", "UPPER@EXAMPLE.COM"), invalid_row])

    preview = build_preview_rows(db, content)
    assert [row.is_valid for row in preview] == [True, False]
    assert db.query(Candidate).count() == 0

    upload = UploadFile(filename="candidates.xlsx", file=BytesIO(content))
    result = asyncio.run(import_candidates_from_excel(db, upload))

    assert result.model_dump() == {
        "imported": 1,
        "skipped": 1,
        "errors": ["Row 3: CANDIDATE_FIELD_INVALID: Invalid Email: invalid-email"],
    }
    imported = db.query(Candidate).one()
    assert imported.application_id == "APP-VALID"
    assert imported.email == "upper@example.com"
    assert imported.stage == "CV_SCREENING"
    assert imported.status == "PASS_CV"
