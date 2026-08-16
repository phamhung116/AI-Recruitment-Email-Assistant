"""Resend HTTP adapter with deterministic response normalization."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from time import perf_counter
from uuid import UUID

import httpx

from app.models import FailureCategory, OperationStatus


RESEND_EMAILS_URL = "https://api.resend.com/emails"
USER_AGENT = "recruitment-mail-guard/0.1"
MAX_PROVIDER_ERROR_LENGTH = 500


class ResendConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class ResendEmail:
    to_email: str
    subject: str
    body: str


@dataclass(frozen=True)
class ResendSendResult:
    outcome: str
    payload_digest: str
    latency_ms: int
    http_status_code: int | None = None
    provider_message_id: str | None = None
    failure_category: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class ResendEmailAdapter:
    def __init__(
        self,
        *,
        api_key: str | None,
        sender_address: str,
        sender_name: str,
        connect_timeout_seconds: float = 5.0,
        read_timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        normalized_key = (api_key or "").strip()
        if not normalized_key:
            raise ResendConfigurationError("RESEND_API_KEY is required.")
        if not sender_address.strip():
            raise ResendConfigurationError("EMAIL_SENDER_ADDRESS is required.")

        self._api_key = normalized_key
        self._sender_address = sender_address.strip()
        self._sender_name = sender_name.strip()
        self._timeout = httpx.Timeout(
            read_timeout_seconds,
            connect=connect_timeout_seconds,
        )
        self._transport = transport

    def send_email(
        self,
        *,
        operation_id: UUID,
        email: ResendEmail,
    ) -> ResendSendResult:
        payload = self.build_payload(email)
        payload_digest = digest_payload(payload)
        started_at = perf_counter()

        try:
            with httpx.Client(
                timeout=self._timeout,
                transport=self._transport,
            ) as client:
                response = client.post(
                    RESEND_EMAILS_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Idempotency-Key": str(operation_id),
                        "User-Agent": USER_AGENT,
                    },
                    json=payload,
                )
        except (httpx.TimeoutException, httpx.NetworkError):
            return ResendSendResult(
                outcome=OperationStatus.DELIVERY_UNKNOWN.value,
                payload_digest=payload_digest,
                latency_ms=_elapsed_ms(started_at),
                error_code="PROVIDER_RESPONSE_UNKNOWN",
                error_message=(
                    "The provider response was not received. Verify provider status before retrying."
                ),
            )

        latency_ms = _elapsed_ms(started_at)
        if response.status_code in {200, 201}:
            provider_message_id = _response_message_id(response)
            if provider_message_id:
                return ResendSendResult(
                    outcome=OperationStatus.PROVIDER_ACCEPTED.value,
                    payload_digest=payload_digest,
                    latency_ms=latency_ms,
                    http_status_code=response.status_code,
                    provider_message_id=provider_message_id,
                )

            return ResendSendResult(
                outcome=OperationStatus.DELIVERY_UNKNOWN.value,
                payload_digest=payload_digest,
                latency_ms=latency_ms,
                http_status_code=response.status_code,
                error_code="PROVIDER_RESPONSE_INVALID",
                error_message=(
                    "The provider accepted the request but returned no message identifier. "
                    "Verify provider status before retrying."
                ),
            )

        error_code, error_message = _provider_error(response)
        return ResendSendResult(
            outcome=OperationStatus.DEFINITIVE_FAILURE.value,
            payload_digest=payload_digest,
            latency_ms=latency_ms,
            http_status_code=response.status_code,
            failure_category=_failure_category(response.status_code),
            error_code=error_code,
            error_message=error_message,
        )

    def build_payload(self, email: ResendEmail) -> dict[str, object]:
        sender = self._sender_address
        if self._sender_name:
            sender = f"{self._sender_name} <{sender}>"
        return {
            "from": sender,
            "to": [email.to_email],
            "subject": email.subject,
            "text": email.body,
        }


def digest_payload(payload: dict[str, object]) -> str:
    canonical_payload = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return sha256(canonical_payload).hexdigest()


def _elapsed_ms(started_at: float) -> int:
    return max(0, round((perf_counter() - started_at) * 1000))


def _response_message_id(response: httpx.Response) -> str | None:
    try:
        response_data = response.json()
    except ValueError:
        return None
    if not isinstance(response_data, dict):
        return None
    message_id = response_data.get("id")
    return message_id.strip() if isinstance(message_id, str) and message_id.strip() else None


def _failure_category(status_code: int) -> str:
    if status_code == 429:
        return FailureCategory.QUOTA_EXCEEDED.value
    if status_code >= 500 or status_code == 409:
        return FailureCategory.TRANSIENT_RETRYABLE.value
    return FailureCategory.VALIDATION_TERMINAL.value


def _provider_error(response: httpx.Response) -> tuple[str, str]:
    default_code = f"RESEND_HTTP_{response.status_code}"
    default_message = "The email provider rejected the request."
    try:
        response_data = response.json()
    except ValueError:
        return default_code, default_message
    if not isinstance(response_data, dict):
        return default_code, default_message

    raw_code = response_data.get("name") or response_data.get("code")
    raw_message = response_data.get("message")
    error_code = raw_code.strip() if isinstance(raw_code, str) and raw_code.strip() else default_code
    error_message = (
        raw_message.strip()
        if isinstance(raw_message, str) and raw_message.strip()
        else default_message
    )
    return error_code[:100], error_message[:MAX_PROVIDER_ERROR_LENGTH]
