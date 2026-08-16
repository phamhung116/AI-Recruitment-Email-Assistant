from __future__ import annotations

from uuid import UUID

import httpx
import pytest

from app.adapters.resend_adapter import (
    ResendConfigurationError,
    ResendEmail,
    ResendEmailAdapter,
    digest_payload,
)
from app.models import FailureCategory, OperationStatus


OPERATION_ID = UUID("11111111-2222-3333-4444-555555555555")
EMAIL = ResendEmail(
    to_email="candidate@example.com",
    subject="Application update",
    body="Hello candidate",
)


def adapter_for(handler) -> ResendEmailAdapter:
    return ResendEmailAdapter(
        api_key="re_test_secret",
        sender_address="onboarding@resend.dev",
        sender_name="Recruitment Team",
        transport=httpx.MockTransport(handler),
    )


def test_success_uses_resend_contract_and_returns_message_id() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        captured["payload"] = request.read()
        return httpx.Response(200, json={"id": "email_123"})

    result = adapter_for(handler).send_email(operation_id=OPERATION_ID, email=EMAIL)

    assert result.outcome == OperationStatus.PROVIDER_ACCEPTED.value
    assert result.provider_message_id == "email_123"
    assert result.http_status_code == 200
    headers = captured["headers"]
    assert isinstance(headers, httpx.Headers)
    assert headers["Authorization"] == "Bearer re_test_secret"
    assert headers["Idempotency-Key"] == str(OPERATION_ID)
    assert headers["User-Agent"] == "recruitment-mail-guard/0.1"

    expected_payload = {
        "from": "Recruitment Team <onboarding@resend.dev>",
        "to": ["candidate@example.com"],
        "subject": "Application update",
        "text": "Hello candidate",
    }
    assert result.payload_digest == digest_payload(expected_payload)


@pytest.mark.parametrize("status_code", [400, 422])
def test_validation_error_is_terminal(status_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            json={"name": "validation_error", "message": "Recipient is invalid"},
        )

    result = adapter_for(handler).send_email(operation_id=OPERATION_ID, email=EMAIL)

    assert result.outcome == OperationStatus.DEFINITIVE_FAILURE.value
    assert result.failure_category == FailureCategory.VALIDATION_TERMINAL.value
    assert result.error_code == "validation_error"
    assert result.error_message == "Recipient is invalid"


def test_server_error_is_retryable_definitive_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"message": "Service unavailable"})

    result = adapter_for(handler).send_email(operation_id=OPERATION_ID, email=EMAIL)

    assert result.outcome == OperationStatus.DEFINITIVE_FAILURE.value
    assert result.failure_category == FailureCategory.TRANSIENT_RETRYABLE.value
    assert result.http_status_code == 503


def test_rate_limit_is_normalized_as_quota_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"name": "rate_limit_exceeded"})

    result = adapter_for(handler).send_email(operation_id=OPERATION_ID, email=EMAIL)

    assert result.outcome == OperationStatus.DEFINITIVE_FAILURE.value
    assert result.failure_category == FailureCategory.QUOTA_EXCEEDED.value


def test_timeout_becomes_delivery_unknown_without_leaking_exception() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("secret provider detail", request=request)

    result = adapter_for(handler).send_email(operation_id=OPERATION_ID, email=EMAIL)

    assert result.outcome == OperationStatus.DELIVERY_UNKNOWN.value
    assert result.http_status_code is None
    assert result.error_code == "PROVIDER_RESPONSE_UNKNOWN"
    assert "secret provider detail" not in (result.error_message or "")


def test_success_without_message_id_is_delivery_unknown() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    result = adapter_for(handler).send_email(operation_id=OPERATION_ID, email=EMAIL)

    assert result.outcome == OperationStatus.DELIVERY_UNKNOWN.value
    assert result.error_code == "PROVIDER_RESPONSE_INVALID"


def test_payload_digest_is_canonical() -> None:
    first = {"subject": "Hello", "to": ["a@example.com"]}
    second = {"to": ["a@example.com"], "subject": "Hello"}

    assert digest_payload(first) == digest_payload(second)
    assert len(digest_payload(first)) == 64


def test_missing_api_key_fails_before_network_use() -> None:
    with pytest.raises(ResendConfigurationError, match="RESEND_API_KEY"):
        ResendEmailAdapter(
            api_key=" ",
            sender_address="onboarding@resend.dev",
            sender_name="Recruitment Team",
        )
