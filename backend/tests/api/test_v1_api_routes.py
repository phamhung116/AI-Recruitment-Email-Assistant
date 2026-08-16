from __future__ import annotations

from collections.abc import Iterator
from io import BytesIO

import httpx
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.resend_adapter import ResendEmailAdapter
from app.api.v1.dependencies import get_resend_adapter, get_session_factory
from app.db.database import Base, build_engine, get_db
from app.main import create_app


@pytest.fixture
def api_client(tmp_path) -> Iterator[tuple[TestClient, sessionmaker[Session], list[str]]]:
    engine = build_engine(f"sqlite+pysqlite:///{tmp_path / 'api.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    provider_calls: list[str] = []

    def db_override() -> Iterator[Session]:
        db = factory()
        try:
            yield db
        finally:
            db.close()

    def provider_handler(request: httpx.Request) -> httpx.Response:
        provider_calls.append(request.headers["Idempotency-Key"])
        return httpx.Response(200, json={"id": "email_api_123"})

    adapter = ResendEmailAdapter(
        api_key="re_test_secret",
        sender_address="onboarding@resend.dev",
        sender_name="Recruitment Team",
        transport=httpx.MockTransport(provider_handler),
    )
    app = create_app()
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_session_factory] = lambda: factory
    app.dependency_overrides[get_resend_adapter] = lambda: adapter

    with TestClient(app) as client:
        yield client, factory, provider_calls

    Base.metadata.drop_all(engine)
    engine.dispose()


def excel_file() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["application_id", "candidate_name", "email", "stage", "status"])
    sheet.append(
        ["APP-API-001", "Nguyen Van A", "candidate@example.com", "INTERVIEW", "PASS_INTERVIEW"]
    )
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def import_candidate(client: TestClient) -> None:
    preview = client.post(
        "/api/v1/candidates/import/preview",
        files={"file": ("candidates.xlsx", excel_file(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert preview.status_code == 200
    assert preview.json()["valid_rows"] == 1

    imported = client.post(
        "/api/v1/candidates/import",
        files={"file": ("candidates.xlsx", excel_file(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert imported.status_code == 200
    assert imported.json() == {"imported": 1, "skipped": 0, "errors": []}


def test_import_draft_confirm_send_and_audit_round_trip(api_client) -> None:
    client, _, provider_calls = api_client
    import_candidate(client)

    candidates = client.get("/api/v1/candidates", params={"status": "PASS_INTERVIEW"})
    assert candidates.status_code == 200
    assert candidates.json()["total"] == 1

    draft_response = client.post(
        "/api/v1/drafts",
        json={"application_id": "APP-API-001", "actor": "hr.author"},
    )
    assert draft_response.status_code == 201
    draft = draft_response.json()
    assert draft["status"] == "READY_TO_SEND"

    revisions = client.get(f"/api/v1/candidates/{candidates.json()['items'][0]['id']}/drafts")
    assert revisions.status_code == 200
    assert revisions.json()["items"][0]["id"] == draft["id"]

    blocked = client.post(
        f"/api/v1/drafts/{draft['id']}/send",
        json={"actor": "hr.sender", "confirmation_acknowledged": False},
    )
    assert blocked.status_code == 422
    assert blocked.json()["error_code"] == "SEND_CONFIRMATION_REQUIRED"
    assert provider_calls == []

    sent = client.post(
        f"/api/v1/drafts/{draft['id']}/send",
        json={"actor": "hr.sender", "confirmation_acknowledged": True},
    )
    assert sent.status_code == 200
    operation = sent.json()
    assert operation["operation_status"] == "PROVIDER_ACCEPTED"
    assert len(operation["attempts"]) == 1

    repeated = client.post(
        f"/api/v1/drafts/{draft['id']}/send",
        json={"actor": "hr.sender", "confirmation_acknowledged": True},
    )
    assert repeated.status_code == 200
    assert repeated.json()["id"] == operation["id"]
    assert len(provider_calls) == 1

    audits = client.get("/api/v1/audit-logs", params={"application_id": "APP-API-001"})
    assert audits.status_code == 200
    event_names = {item["event_name"] for item in audits.json()["items"]}
    assert {
        "CANDIDATE_IMPORTED",
        "DRAFT_GENERATED",
        "SEND_PREPARED",
        "SEND_OUTCOME_FINALIZED",
    }.issubset(event_names)


def test_list_contract_validates_page_size(api_client) -> None:
    client, _, _ = api_client
    response = client.get("/api/v1/candidates", params={"page_size": 101})
    assert response.status_code == 422
    assert response.json()["error_code"] == "REQUEST_VALIDATION_FAILED"
    assert response.json()["details"]["fields"][0]["location"] == "query.page_size"
