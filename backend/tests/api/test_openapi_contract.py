from app.main import create_app


def test_real_email_routes_are_present_in_openapi() -> None:
    schema = create_app().openapi()
    paths = schema["paths"]

    assert "post" in paths["/api/v1/drafts/{draft_revision_id}/send"]
    assert "post" in paths["/api/v1/send-operations/{operation_id}/retry"]
    assert "post" in paths["/api/v1/send-operations/{operation_id}/reconcile"]
    assert "post" in paths["/api/v1/send-operations/{operation_id}/resolve"]
    assert "get" in paths["/api/v1/audit-logs"]
    assert "get" in paths["/api/v1/candidates/{candidate_id}/drafts"]


def test_send_route_exposes_confirmation_and_operation_response() -> None:
    operation = create_app().openapi()["paths"][
        "/api/v1/drafts/{draft_revision_id}/send"
    ]["post"]

    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]

    assert request_schema["$ref"].endswith("/SendConfirmationRequest")
    assert response_schema["$ref"].endswith("/SendOperationRead")
